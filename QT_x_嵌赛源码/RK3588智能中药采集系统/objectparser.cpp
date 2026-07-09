#include "objectparser.h"

#include <QStringList>

ObjectRecognitionResult ObjectParser::parse(const QString &rawOutput)
{
    ObjectRecognitionResult result;
    result.rawOutput = rawOutput.trimmed();

    if (result.rawOutput.isEmpty()) {
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

    result.objectName = extractField(QStringLiteral("物品名称"));
    result.category = extractField(QStringLiteral("物品类别"));
    result.appearance = extractField(QStringLiteral("外观特征"));
    result.description = extractField(QStringLiteral("详细描述"));

    const QString failure = extractField(QStringLiteral("识别失败"));
    if (!failure.isEmpty()) {
        result.success = false;
        result.rawOutput = failure;
        return result;
    }

    result.success = !result.objectName.isEmpty();
    if (!result.success && !result.description.isEmpty()) {
        result.success = true;
        result.objectName = QStringLiteral("未知物品");
    }

    return result;
}
