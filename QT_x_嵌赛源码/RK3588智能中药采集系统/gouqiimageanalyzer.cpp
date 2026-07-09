#include "gouqiimageanalyzer.h"

namespace {
const double kMinGlobalRedRatio = 0.04;
const double kMaxGlobalRedRatio = 0.68;
const double kMinLocalRedRatio = 0.10;
const double kMinClusterCellRatio = 0.08;
const int kGridCols = 10;
const int kGridRows = 8;
const int kMinRedClusterCells = 1;

bool isSkinLikePixel(int r, int g, int b)
{
    return r > 55 && g > 35 && b > 25 && r >= g && (r - g) < 55 && (g - b) < 45;
}

double redRatioInRect(const QImage &rgb, const QRect &rect, int &redCount)
{
    redCount = 0;
    int total = 0;

    const QRect bounds(0, 0, rgb.width(), rgb.height());
    const QRect area = rect.intersected(bounds);
    if (area.isEmpty()) {
        return 0.0;
    }

    for (int y = area.top(); y <= area.bottom(); ++y) {
        const QRgb *line = reinterpret_cast<const QRgb *>(rgb.constScanLine(y));
        for (int x = area.left(); x <= area.right(); ++x) {
            const QRgb pixel = line[x];
            if (GouqiImageAnalyzer::isGouqiRedPixel(qRed(pixel), qGreen(pixel), qBlue(pixel))) {
                ++redCount;
            }
            ++total;
        }
    }

    if (total == 0) {
        return 0.0;
    }
    return static_cast<double>(redCount) / static_cast<double>(total);
}

double computeConfidence(const GouqiImageAnalyzer::Result &result)
{
    if (!result.likelyGouqi) {
        return 0.0;
    }

    const double globalScore = qBound(0.0, (result.redPixelRatio - 0.03) / 0.28, 1.0);
    const double localScore = qBound(0.0, (result.localRedRatio - 0.08) / 0.38, 1.0);
    const double clusterScore = qBound(0.0, static_cast<double>(result.redClusterCells) / 4.0, 1.0);
    return qBound(0.0, localScore * 0.50 + globalScore * 0.30 + clusterScore * 0.20, 0.95);
}

} // namespace

double GouqiImageAnalyzer::computeDetectConfidence(const Result &analyze,
                                                   const QImage &image,
                                                   const QRect &bbox)
{
    if (image.isNull() || !bbox.isValid() || !analyze.likelyGouqi) {
        return 0.0;
    }

    const QImage rgb = image.convertToFormat(QImage::Format_RGB32);
    int redCount = 0;
    const double boxRedRatio = redRatioInRect(rgb, bbox, redCount);

    const int imageArea = qMax(1, rgb.width() * rgb.height());
    const double boxAreaRatio = static_cast<double>(bbox.width() * bbox.height()) / imageArea;

    const double boxScore = qBound(0.0, (boxRedRatio - 0.06) / 0.42, 1.0);

    double sizeScore = 1.0;
    if (boxAreaRatio < 0.015) {
        sizeScore = qBound(0.25, boxAreaRatio / 0.015, 1.0);
    } else if (boxAreaRatio > 0.35) {
        sizeScore = qBound(0.20, 1.0 - (boxAreaRatio - 0.35) / 0.45, 1.0);
    } else {
        const double ideal = 0.12;
        sizeScore = 1.0 - qMin(1.0, qAbs(boxAreaRatio - ideal) / 0.22) * 0.35;
    }

    const double clusterScore = qBound(0.0, static_cast<double>(analyze.redClusterCells) / 4.0, 1.0);
    const double conf = analyze.confidence * 0.35
                        + boxScore * 0.35
                        + sizeScore * 0.20
                        + clusterScore * 0.10;
    return qBound(0.32, conf, 0.97);
}

bool GouqiImageAnalyzer::isGouqiRedPixel(int r, int g, int b)
{
    if (isSkinLikePixel(r, g, b)) {
        return false;
    }

    const int maxGB = qMax(g, b);
    const int redLead = r - maxGB;

    // 鲜红/亮红枸杞
    if (r > 105 && g < 95 && b < 95 && redLead > 22) {
        return true;
    }
    if (r > 115 && g < 85 && b < 85 && r > g + 28 && r > b + 28) {
        return true;
    }

    // 暗红/深红枸杞（摄像头、室内光、干枸杞常见）
    if (r >= 68 && g <= 105 && b <= 105 && redLead >= 14 && redLead <= 95) {
        return r > g + 10 && r > b + 10;
    }

    return false;
}

bool GouqiImageAnalyzer::isConfidentGouqi(const Result &result)
{
    return result.likelyGouqi && result.confidence >= 0.48;
}

GouqiImageAnalyzer::Result GouqiImageAnalyzer::analyze(const QImage &image)
{
    Result result;

    if (image.isNull()) {
        return result;
    }

    const QImage rgb = image.convertToFormat(QImage::Format_RGB32);
    int globalRedCount = 0;
    result.redPixelRatio = redRatioInRect(rgb, QRect(0, 0, rgb.width(), rgb.height()), globalRedCount);

    const int cellW = qMax(1, rgb.width() / kGridCols);
    const int cellH = qMax(1, rgb.height() / kGridRows);
    double maxLocalRatio = 0.0;
    int clusterCells = 0;

    for (int row = 0; row < kGridRows; ++row) {
        for (int col = 0; col < kGridCols; ++col) {
            const QRect cell(col * cellW, row * cellH, cellW, cellH);
            int redCount = 0;
            const double localRatio = redRatioInRect(rgb, cell, redCount);
            if (localRatio >= kMinClusterCellRatio) {
                ++clusterCells;
            }
            if (localRatio > maxLocalRatio) {
                maxLocalRatio = localRatio;
                result.focusRegion = cell;
            }
        }
    }

    result.localRedRatio = maxLocalRatio;
    result.redClusterCells = clusterCells;

    const bool globalMatch = result.redPixelRatio >= kMinGlobalRedRatio
                             && result.redPixelRatio <= kMaxGlobalRedRatio;
    const bool localMatch = result.localRedRatio >= kMinLocalRedRatio;
    const bool clusterMatch = clusterCells >= kMinRedClusterCells;

    result.likelyGouqi = (globalMatch && localMatch)
                         || (localMatch && clusterMatch && result.redPixelRatio >= 0.03);
    result.confidence = computeConfidence(result);
    return result;
}
