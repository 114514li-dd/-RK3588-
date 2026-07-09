#include "imagepreprocessor.h"
#include "platformpaths.h"

#include <QDateTime>
#include <QDir>
#include <QFileInfo>

#ifdef HAS_OPENCV
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

#include <string>
#include <vector>
#endif

namespace {
const double kEdgeCropRatio = 0.10;
const double kContrastAlpha = 1.15;
const double kBrightnessBeta = 15.0;
const int kOutputSize = 640;
const double kDetectContrastAlpha = 1.28;
const double kDetectBrightnessBeta = 18.0;
const double kDetectSaturationBoost = 1.22;

QImage enhanceForDetectionQt(const QImage &source)
{
    if (source.isNull()) {
        return source;
    }
    QImage image = source.convertToFormat(QImage::Format_RGB32);
    for (int y = 0; y < image.height(); ++y) {
        QRgb *line = reinterpret_cast<QRgb *>(image.scanLine(y));
        for (int x = 0; x < image.width(); ++x) {
            int r = qBound(0, static_cast<int>(qRed(line[x]) * kDetectContrastAlpha + kDetectBrightnessBeta), 255);
            int g = qBound(0, static_cast<int>(qGreen(line[x]) * kDetectContrastAlpha + kDetectBrightnessBeta), 255);
            int b = qBound(0, static_cast<int>(qBlue(line[x]) * kDetectContrastAlpha + kDetectBrightnessBeta), 255);
            const int gray = (r + g + b) / 3;
            r = qBound(0, static_cast<int>(gray + (r - gray) * kDetectSaturationBoost), 255);
            g = qBound(0, static_cast<int>(gray + (g - gray) * kDetectSaturationBoost), 255);
            b = qBound(0, static_cast<int>(gray + (b - gray) * kDetectSaturationBoost), 255);
            line[x] = qRgb(r, g, b);
        }
    }
    return image;
}

} // namespace

QString ImagePreprocessor::defaultProcessedPath()
{
    const QString fileName = QStringLiteral("processed_%1.jpg")
                                 .arg(QDateTime::currentDateTime().toString(QStringLiteral("yyyyMMdd_hhmmss")));
    return QDir(PlatformPaths::tempCaptureDir()).filePath(fileName);
}

bool ImagePreprocessor::isAvailable()
{
    return true;
}

#ifdef HAS_OPENCV

namespace {

cv::Mat qImageToBgrMat(const QImage &image)
{
    QImage rgb = image.convertToFormat(QImage::Format_RGB888);
    cv::Mat mat(rgb.height(), rgb.width(), CV_8UC3,
                const_cast<uchar *>(rgb.bits()), static_cast<size_t>(rgb.bytesPerLine()));
    cv::Mat bgr;
    cv::cvtColor(mat, bgr, cv::COLOR_RGB2BGR);
    return bgr.clone();
}

QImage bgrMatToQImage(const cv::Mat &mat)
{
    cv::Mat rgb;
    cv::cvtColor(mat, rgb, cv::COLOR_BGR2RGB);
    return QImage(rgb.data, rgb.cols, rgb.rows, static_cast<int>(rgb.step),
                  QImage::Format_RGB888)
        .copy();
}

cv::Mat cropCenterRegion(const cv::Mat &source)
{
    const int marginX = static_cast<int>(source.cols * kEdgeCropRatio);
    const int marginY = static_cast<int>(source.rows * kEdgeCropRatio);
    const int cropWidth = source.cols - marginX * 2;
    const int cropHeight = source.rows - marginY * 2;

    if (cropWidth <= 0 || cropHeight <= 0) {
        return cv::Mat();
    }

    const cv::Rect roi(marginX, marginY, cropWidth, cropHeight);
    return source(roi).clone();
}

bool saveCvMat(const cv::Mat &mat, const QString &outputPath)
{
#ifdef Q_OS_WIN
    const std::string filePath = outputPath.toLocal8Bit().constData();
#else
    const std::string filePath = outputPath.toUtf8().constData();
#endif
    return cv::imwrite(filePath, mat);
}

} // namespace

ImagePreprocessor::Result ImagePreprocessor::processWithOpenCV(const QImage &source,
                                                                const QString &outputPath)
{
    Result result;

    const cv::Mat bgr = qImageToBgrMat(source);
    if (bgr.empty()) {
        result.errorMessage = QStringLiteral("图片格式转换失败");
        return result;
    }

    const cv::Mat cropped = cropCenterRegion(bgr);
    if (cropped.empty()) {
        result.errorMessage = QStringLiteral("中心区域裁剪失败，图片尺寸过小");
        return result;
    }

    cv::Mat adjusted;
    cropped.convertTo(adjusted, -1, kContrastAlpha, kBrightnessBeta);

    cv::Mat resized;
    cv::resize(adjusted, resized, cv::Size(kOutputSize, kOutputSize), 0, 0, cv::INTER_LINEAR);
    if (resized.empty()) {
        result.errorMessage = QStringLiteral("图片缩放失败");
        return result;
    }

    if (!saveCvMat(resized, outputPath)) {
        result.errorMessage = QStringLiteral("预处理图片保存失败，请检查临时目录权限");
        return result;
    }

    result.image = bgrMatToQImage(resized);
    if (result.image.isNull()) {
        result.errorMessage = QStringLiteral("预处理结果转换失败");
        return result;
    }

    result.success = true;
    return result;
}

#else

namespace {

QImage cropCenterRegionQt(const QImage &source)
{
    const int marginX = static_cast<int>(source.width() * kEdgeCropRatio);
    const int marginY = static_cast<int>(source.height() * kEdgeCropRatio);
    const int cropWidth = source.width() - marginX * 2;
    const int cropHeight = source.height() - marginY * 2;

    if (cropWidth <= 0 || cropHeight <= 0) {
        return QImage();
    }

    return source.copy(marginX, marginY, cropWidth, cropHeight);
}

QImage adjustBrightnessContrastQt(const QImage &source)
{
    QImage image = source.convertToFormat(QImage::Format_RGB32);
    for (int y = 0; y < image.height(); ++y) {
        QRgb *line = reinterpret_cast<QRgb *>(image.scanLine(y));
        for (int x = 0; x < image.width(); ++x) {
            const int r = qBound(0, static_cast<int>(qRed(line[x]) * kContrastAlpha + kBrightnessBeta), 255);
            const int g = qBound(0, static_cast<int>(qGreen(line[x]) * kContrastAlpha + kBrightnessBeta), 255);
            const int b = qBound(0, static_cast<int>(qBlue(line[x]) * kContrastAlpha + kBrightnessBeta), 255);
            line[x] = qRgb(r, g, b);
        }
    }
    return image;
}

} // namespace

ImagePreprocessor::Result ImagePreprocessor::processWithOpenCV(const QImage &source,
                                                                const QString &outputPath)
{
    Result result;

    const QImage cropped = cropCenterRegionQt(source);
    if (cropped.isNull()) {
        result.errorMessage = QStringLiteral("中心区域裁剪失败，图片尺寸过小");
        return result;
    }

    const QImage adjusted = adjustBrightnessContrastQt(cropped);
    const QImage resized = adjusted.scaled(kOutputSize, kOutputSize,
                                           Qt::IgnoreAspectRatio,
                                           Qt::SmoothTransformation);
    if (resized.isNull()) {
        result.errorMessage = QStringLiteral("图片缩放失败");
        return result;
    }

    if (!resized.save(outputPath, "JPG", 90)) {
        result.errorMessage = QStringLiteral("预处理图片保存失败，请检查临时目录权限");
        return result;
    }

    result.image = resized;
    result.success = true;
    return result;
}

#endif

QImage ImagePreprocessor::enhanceForDetection(const QImage &source)
{
#ifdef HAS_OPENCV
    const cv::Mat bgr = qImageToBgrMat(source);
    if (bgr.empty()) {
        return enhanceForDetectionQt(source);
    }

    cv::Mat adjusted;
    bgr.convertTo(adjusted, -1, kDetectContrastAlpha, kDetectBrightnessBeta);

    cv::Mat hsv;
    cv::cvtColor(adjusted, hsv, cv::COLOR_BGR2HSV);
    std::vector<cv::Mat> channels;
    cv::split(hsv, channels);
    channels.at(1) *= kDetectSaturationBoost;
    cv::merge(channels, hsv);
    cv::cvtColor(hsv, adjusted, cv::COLOR_HSV2BGR);

    return bgrMatToQImage(adjusted);
#else
    return enhanceForDetectionQt(source);
#endif
}

ImagePreprocessor::Result ImagePreprocessor::processAndSave(const QImage &source,
                                                            const QString &outputPath)
{
    Result result;
    result.success = false;

    if (source.isNull()) {
        result.errorMessage = QStringLiteral("输入图片无效");
        return result;
    }

    const QString savePath = outputPath.isEmpty() ? defaultProcessedPath() : outputPath;
    const QFileInfo fileInfo(savePath);
    QDir().mkpath(fileInfo.absolutePath());

    result = processWithOpenCV(source, savePath);
    if (result.success) {
        result.savedPath = savePath;
    }
    return result;
}

ImagePreprocessor::Result ImagePreprocessor::processAndSaveFullFrame(const QImage &source,
                                                                      const QString &outputPath)
{
    Result result;
    result.success = false;

    if (source.isNull()) {
        result.errorMessage = QStringLiteral("输入图片无效");
        return result;
    }

    const QString savePath = outputPath.isEmpty() ? defaultProcessedPath() : outputPath;
    const QFileInfo fileInfo(savePath);
    QDir().mkpath(fileInfo.absolutePath());

    QImage scaled = source.convertToFormat(QImage::Format_RGB888)
                          .scaled(kOutputSize, kOutputSize, Qt::KeepAspectRatio, Qt::SmoothTransformation);
    if (scaled.isNull()) {
        result.errorMessage = QStringLiteral("图片缩放失败");
        return result;
    }

    if (!scaled.save(savePath, "JPG", 90)) {
        result.errorMessage = QStringLiteral("图片保存失败，请检查临时目录权限");
        return result;
    }

    result.image = scaled;
    result.savedPath = savePath;
    result.success = true;
    return result;
}
