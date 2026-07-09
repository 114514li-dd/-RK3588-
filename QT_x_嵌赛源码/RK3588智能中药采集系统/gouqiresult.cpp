#include "gouqiresult.h"

#include <QStringList>

QString GouqiRecognitionResult::detailText() const
{
    QStringList lines;
    if (!propertyChannel.isEmpty()) {
        lines << QStringLiteral("【性味归经】%1").arg(propertyChannel);
    }
    if (!efficacy.isEmpty()) {
        lines << QStringLiteral("【功效】%1").arg(efficacy);
    }
    if (!usage.isEmpty()) {
        lines << QStringLiteral("【用法用量】%1").arg(usage);
    }
    if (!contraindication.isEmpty()) {
        lines << QStringLiteral("【禁忌】%1").arg(contraindication);
    }
    if (!authenticityTips.isEmpty()) {
        lines << QStringLiteral("【真伪鉴别要点】%1").arg(authenticityTips);
    }
    return lines.join(QLatin1Char('\n'));
}
