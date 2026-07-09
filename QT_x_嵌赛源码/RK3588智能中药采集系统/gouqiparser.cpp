#include "gouqiparser.h"

#include <QStringList>

GouqiRecognitionResult GouqiParser::parse(const QString &rawOutput)
{
    GouqiRecognitionResult result;

    if (isNotRecognized(rawOutput)) {
        result.recognized = false;
        result.drugName = QStringLiteral("未识别到枸杞");
        return result;
    }

    const auto extractField = [&rawOutput](const QString &key) -> QString {
        const QString tag = QStringLiteral("【") + key + QStringLiteral("】");
        const QStringList lines = rawOutput.split(QLatin1Char('\n'));
        for (int i = 0; i < lines.size(); ++i) {
            const QString line = lines.at(i).trimmed();
            if (line.startsWith(tag)) {
                return line.mid(tag.length()).trimmed();
            }
        }
        return QString();
    };

    result.drugName = extractField(QStringLiteral("药品名称"));
    result.category = extractField(QStringLiteral("药材分类"));
    result.propertyChannel = extractField(QStringLiteral("性味归经"));
    result.efficacy = extractField(QStringLiteral("功效"));
    result.usage = extractField(QStringLiteral("用法用量"));
    if (result.usage.isEmpty()) {
        result.usage = extractField(QStringLiteral("用法"));
    }
    result.contraindication = extractField(QStringLiteral("禁忌"));
    result.authenticityTips = extractField(QStringLiteral("真伪鉴别要点"));

    result.recognized = !result.drugName.isEmpty()
                        && !result.drugName.contains(QStringLiteral("未识别到枸杞"));
    return result;
}

bool GouqiParser::isNotRecognized(const QString &rawOutput)
{
    return rawOutput.contains(QStringLiteral("未识别到枸杞"));
}
