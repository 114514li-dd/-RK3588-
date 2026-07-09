#ifndef IMAGEPREPROCESSOR_H
#define IMAGEPREPROCESSOR_H

#include <QImage>
#include <QString>

/**
 * @brief 抓拍图片预处理模块
 * 裁剪中心区域（去除 10% 边缘）、调整亮度对比度、缩放到 640x640。
 */
class ImagePreprocessor
{
public:
    struct Result {
        bool success;
        QString errorMessage;
        QImage image;
        QString savedPath;
    };

    static bool isAvailable();
    static Result processAndSave(const QImage &source, const QString &outputPath = QString());
    static Result processAndSaveFullFrame(const QImage &source, const QString &outputPath = QString());
    /** 摄像头抓拍增强：提升对比度/饱和度，不改变尺寸，供颜色检测使用 */
    static QImage enhanceForDetection(const QImage &source);
    static QString defaultProcessedPath();

private:
    static Result processWithOpenCV(const QImage &source, const QString &outputPath);
};

#endif // IMAGEPREPROCESSOR_H
