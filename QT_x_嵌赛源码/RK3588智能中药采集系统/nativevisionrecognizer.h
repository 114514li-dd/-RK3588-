#ifndef NATIVEVISIONRECOGNIZER_H
#define NATIVEVISIONRECOGNIZER_H

#include "gouqiresult.h"
#include "objectrecognitionresult.h"

#include <QImage>
#include <QString>

class NativeVisionRecognizer
{
public:
    static QImage loadImage(const QString &path);
    static QString buildGouqiOutput(const QImage &image);
    static QString buildObjectOutput(const QImage &image);
    static GouqiRecognitionResult recognizeGouqi(const QImage &image);
    static ObjectRecognitionResult recognizeObject(const QImage &image);
};

#endif // NATIVEVISIONRECOGNIZER_H
