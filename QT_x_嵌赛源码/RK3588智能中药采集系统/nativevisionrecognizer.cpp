#include "nativevisionrecognizer.h"

#include "gouqiparser.h"
#include "gouqiimageanalyzer.h"
#include "objectparser.h"

#include <QFile>

namespace {

QString appearanceText(const GouqiImageAnalyzer::Result &analyze)
{
    if (analyze.localRedRatio >= 0.18 && analyze.redPixelRatio < 0.08) {
        return QStringLiteral(
            "局部区域可见较多红色小颗粒，呈椭圆形，色泽鲜红或暗红，"
            "疑似枸杞或枸杞图片，建议靠近拍摄实物确认。");
    }
    return QStringLiteral(
        "红色小颗粒为主，呈纺锤形或椭圆形，表面具皱纹，颜色偏暗红或鲜红。");
}

QString describeGenericObject(const QImage &image)
{
    const QImage rgb = image.convertToFormat(QImage::Format_RGB32);
    int darkCount = 0;
    int brightCount = 0;
    int skinCount = 0;
    int total = rgb.width() * rgb.height();

    if (total <= 0) {
        return QStringLiteral("无法分析图片内容。");
    }

    int minX = rgb.width();
    int minY = rgb.height();
    int maxX = 0;
    int maxY = 0;
    int darkInCenter = 0;
    int centerTotal = 0;
    const QRect center(rgb.width() / 4, rgb.height() / 4, rgb.width() / 2, rgb.height() / 2);

    for (int y = 0; y < rgb.height(); ++y) {
        const QRgb *line = reinterpret_cast<const QRgb *>(rgb.constScanLine(y));
        for (int x = 0; x < rgb.width(); ++x) {
            const QRgb pixel = line[x];
            const int r = qRed(pixel);
            const int g = qGreen(pixel);
            const int b = qBlue(pixel);
            const int gray = (r + g + b) / 3;

            if (gray < 70) {
                ++darkCount;
                minX = qMin(minX, x);
                minY = qMin(minY, y);
                maxX = qMax(maxX, x);
                maxY = qMax(maxY, y);
            } else if (gray > 190) {
                ++brightCount;
            }

            if (r > 55 && g > 35 && b > 25 && r >= g && (r - g) < 55) {
                ++skinCount;
            }

            if (center.contains(x, y)) {
                ++centerTotal;
                if (gray < 70) {
                    ++darkInCenter;
                }
            }
        }
    }

    const double darkRatio = static_cast<double>(darkCount) / total;
    const double brightRatio = static_cast<double>(brightCount) / total;
    const double skinRatio = static_cast<double>(skinCount) / total;
    const int darkSpanW = qMax(0, maxX - minX);
    const int darkSpanH = qMax(0, maxY - minY);
    const double darkAspect = darkSpanW > 0 && darkSpanH > 0
                                  ? static_cast<double>(qMax(darkSpanW, darkSpanH))
                                        / qMax(1, qMin(darkSpanW, darkSpanH))
                                  : 1.0;

    if (skinRatio > 0.18) {
        return QStringLiteral(
            "【物品名称】\n"
            "【物品类别】\n"
            "【外观特征】未检测到明确的中药材特征。\n"
            "【详细描述】这不是中药材。请对准中药材实物后再识别。");
    }

    if (darkRatio > 0.03 && darkAspect >= 2.0) {
        return QStringLiteral(
            "【物品名称】深色长条状物品\n"
            "【物品类别】文具/日用品\n"
            "【外观特征】画面中有深色细长的物体，可能为笔、工具或其他条形物品。\n"
            "【详细描述】我没有在画面里看到中药材。主体更像深色长条物品，请将待识别物品放在画面中央。");
    }

    if (brightRatio > 0.45 && darkRatio < 0.05) {
        return QStringLiteral(
            "【物品名称】浅色背景场景\n"
            "【物品类别】环境\n"
            "【外观特征】画面整体偏亮，主体不够突出，未检测到枸杞特有的红色颗粒聚集。\n"
            "【详细描述】当前画面里没有明显可确认的中药材，请靠近拍摄并保证主体清晰。");
    }

    if (centerTotal > 0 && static_cast<double>(darkInCenter) / centerTotal > 0.08) {
        return QStringLiteral(
            "【物品名称】中央深色物体\n"
            "【物品类别】未知\n"
            "【外观特征】画面中央有深色物体，但不符合枸杞的红色颗粒特征。\n"
            "【详细描述】暂未识别为枸杞。如需识别药材，请直接拍摄红色枸杞实物。");
    }

    return QStringLiteral(
        "【物品名称】未能确认的物品\n"
        "【物品类别】未知\n"
        "【外观特征】画面中未检测到枸杞特有的红色颗粒聚集特征。\n"
        "【详细描述】这不是枸杞。请将要识别的物品放在画面中央，并保证光线充足。");
}

} // namespace

QImage NativeVisionRecognizer::loadImage(const QString &path)
{
    if (path.isEmpty() || !QFile::exists(path)) {
        return QImage();
    }
    QImage image(path);
    return image;
}

QString NativeVisionRecognizer::buildGouqiOutput(const QImage &image)
{
    const GouqiImageAnalyzer::Result analyze = GouqiImageAnalyzer::analyze(image);
    if (!GouqiImageAnalyzer::isConfidentGouqi(analyze)) {
        return QStringLiteral("未识别到枸杞，请重新拍摄，确保主体清晰、背景干净");
    }

    const QString tips = appearanceText(analyze);
    return QStringLiteral(
               "【药品名称】宁夏枸杞（Lycium barbarum L.）\n"
               "【药材分类】补阴药\n"
               "【性味归经】甘，平。归肝、肾经\n"
               "【功效】滋补肝肾，益精明目\n"
               "【用法用量】6-12g，煎服；也可泡水、煲汤\n"
               "【禁忌】脾虚便溏者慎用\n"
               "【真伪鉴别要点】%1\n"
               "【温度】10~20°C\n"
               "【相对温度】45~60%")
        .arg(tips);
}

QString NativeVisionRecognizer::buildObjectOutput(const QImage &image)
{
    const GouqiImageAnalyzer::Result analyze = GouqiImageAnalyzer::analyze(image);
    if (GouqiImageAnalyzer::isConfidentGouqi(analyze)) {
        const QString appearance = appearanceText(analyze);
        return QStringLiteral(
                   "【物品名称】枸杞\n"
                   "【物品类别】中药材\n"
                   "【外观特征】%1\n"
                   "【详细描述】画面中存在较明确的枸杞红色颗粒特征。如需药材详情，请点击【检测】。")
            .arg(appearance);
    }

    return describeGenericObject(image);
}

GouqiRecognitionResult NativeVisionRecognizer::recognizeGouqi(const QImage &image)
{
    return GouqiParser::parse(buildGouqiOutput(image));
}

ObjectRecognitionResult NativeVisionRecognizer::recognizeObject(const QImage &image)
{
    return ObjectParser::parse(buildObjectOutput(image));
}
