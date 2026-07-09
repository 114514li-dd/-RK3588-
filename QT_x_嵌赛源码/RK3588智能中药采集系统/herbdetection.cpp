#include "herbdetection.h"

#include "gouqiimageanalyzer.h"
#include "imagepreprocessor.h"

#include <QColor>
#include <QImage>

namespace {
const double kGouqiConfidenceThreshold = 0.40;

QRect findGouqiBoundingBox(const QImage &image)
{
    const QImage rgb = image.convertToFormat(QImage::Format_RGB32);
    int minX = rgb.width();
    int minY = rgb.height();
    int maxX = 0;
    int maxY = 0;
    int count = 0;

    for (int y = 0; y < rgb.height(); ++y) {
        const QRgb *line = reinterpret_cast<const QRgb *>(rgb.constScanLine(y));
        for (int x = 0; x < rgb.width(); ++x) {
            const QRgb pixel = line[x];
            if (GouqiImageAnalyzer::isGouqiRedPixel(qRed(pixel), qGreen(pixel), qBlue(pixel))) {
                minX = qMin(minX, x);
                minY = qMin(minY, y);
                maxX = qMax(maxX, x);
                maxY = qMax(maxY, y);
                ++count;
            }
        }
    }

    const int minCount = qMax(8, rgb.width() * rgb.height() / 18000);
    if (count < minCount || maxX <= minX || maxY <= minY) {
        return QRect();
    }

    const int pad = 8;
    return QRect(qMax(0, minX - pad),
                 qMax(0, minY - pad),
                 qMin(rgb.width(), maxX - minX + 1 + pad * 2),
                 qMin(rgb.height(), maxY - minY + 1 + pad * 2));
}

HerbDetectResult detectByColor(const QImage &image)
{
    HerbDetectResult result;
    const GouqiImageAnalyzer::Result analyze = GouqiImageAnalyzer::analyze(image);
    if (!analyze.likelyGouqi) {
        result.success = true;
        return result;
    }

    const QRect bbox = findGouqiBoundingBox(image);
    QRect targetBox = bbox;
    if (targetBox.isEmpty() && analyze.focusRegion.isValid()) {
        targetBox = analyze.focusRegion;
    }
    if (targetBox.isEmpty()) {
        result.success = true;
        return result;
    }

    HerbDetectItem item;
    item.name = QStringLiteral("枸杞");
    item.bbox = targetBox;
    item.confidence = GouqiImageAnalyzer::computeDetectConfidence(analyze, image, targetBox);
    if (item.confidence < kGouqiConfidenceThreshold) {
        result.success = true;
        return result;
    }
    if (!GouqiImageAnalyzer::isConfidentGouqi(analyze)) {
        result.success = true;
        return result;
    }
    result.items.append(item);
    result.success = true;
    return result;
}

} // namespace

bool HerbDetectItem::isGouqi() const
{
    return name.contains(QStringLiteral("枸杞"));
}

HerbDetectItem HerbDetectResult::bestGouqi() const
{
    HerbDetectItem best;
    for (int i = 0; i < items.size(); ++i) {
        if (items.at(i).isGouqi() && items.at(i).confidence > best.confidence) {
            best = items.at(i);
        }
    }
    return best;
}

HerbDetectResult HerbDetector::detect(const QImage &image, const QString &imagePath)
{
    Q_UNUSED(imagePath);

    HerbDetectResult failed;
    if (image.isNull()) {
        failed.errorMessage = QStringLiteral("检测图片无效");
        return failed;
    }

    HerbDetectResult result = detectByColor(image);
    if (!result.items.isEmpty()) {
        return result;
    }

    const QImage enhanced = ImagePreprocessor::enhanceForDetection(image);
    if (!enhanced.isNull()) {
        result = detectByColor(enhanced);
    }
    return result;
}
