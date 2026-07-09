#ifndef GOUQIIMAGEANALYZER_H
#define GOUQIIMAGEANALYZER_H

#include <QImage>
#include <QRect>

/**
 * @brief 枸杞图像特征预检
 * 严格判定，避免人脸/环境红色误报为枸杞。
 */
class GouqiImageAnalyzer
{
public:
    struct Result {
        bool likelyGouqi;
        double confidence;
        double redPixelRatio;
        double localRedRatio;
        int redClusterCells;
        QRect focusRegion;

        Result()
            : likelyGouqi(false),
              confidence(0.0),
              redPixelRatio(0.0),
              localRedRatio(0.0),
              redClusterCells(0)
        {
        }
    };

    static Result analyze(const QImage &image);
    static bool isGouqiRedPixel(int r, int g, int b);
    static bool isConfidentGouqi(const Result &result);
    /** 结合检测框内红色占比、目标大小等，返回随画面变化的动态置信度 */
    static double computeDetectConfidence(const Result &analyze,
                                          const QImage &image,
                                          const QRect &bbox);
};

#endif // GOUQIIMAGEANALYZER_H
