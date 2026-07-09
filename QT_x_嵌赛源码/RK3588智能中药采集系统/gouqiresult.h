#ifndef GOUQIRESULT_H
#define GOUQIRESULT_H

#include <QMetaType>
#include <QString>

struct GouqiRecognitionResult
{
    bool recognized;
    QString drugName;
    QString category;
    QString propertyChannel;
    QString efficacy;
    QString usage;
    QString contraindication;
    QString authenticityTips;
    double confidence;

    GouqiRecognitionResult()
        : recognized(false),
          confidence(0.0)
    {
    }

    QString detailText() const;
};

Q_DECLARE_METATYPE(GouqiRecognitionResult)

#endif // GOUQIRESULT_H
