#include "objectrecognitionresult.h"

#include <QStringList>

QString ObjectRecognitionResult::chatText() const
{
    if (!success) {
        return rawOutput.isEmpty() ? QStringLiteral("识别失败，请重试。") : rawOutput;
    }

    QStringList lines;
    if (!objectName.isEmpty()) {
        lines << QStringLiteral("物品：%1").arg(objectName);
    }
    if (!category.isEmpty()) {
        lines << QStringLiteral("类别：%1").arg(category);
    }
    if (!appearance.isEmpty()) {
        lines << QStringLiteral("外观特征：%1").arg(appearance);
    }
    if (!description.isEmpty()) {
        lines << description;
    }
    if (lines.isEmpty()) {
        return rawOutput;
    }
    return lines.join(QStringLiteral("\n"));
}
