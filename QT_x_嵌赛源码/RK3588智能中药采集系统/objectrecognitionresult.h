#ifndef OBJECTRECOGNITIONRESULT_H
#define OBJECTRECOGNITIONRESULT_H

#include <QMetaType>
#include <QString>

struct ObjectRecognitionResult
{
    bool success;
    QString objectName;
    QString category;
    QString appearance;
    QString description;
    QString rawOutput;

    ObjectRecognitionResult()
        : success(false)
    {
    }

    QString chatText() const;
};

Q_DECLARE_METATYPE(ObjectRecognitionResult)

#endif // OBJECTRECOGNITIONRESULT_H
