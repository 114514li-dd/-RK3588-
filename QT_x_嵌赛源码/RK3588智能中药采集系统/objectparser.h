#ifndef OBJECTPARSER_H
#define OBJECTPARSER_H

#include "objectrecognitionresult.h"

#include <QString>

class ObjectParser
{
public:
    static ObjectRecognitionResult parse(const QString &rawOutput);
};

#endif // OBJECTPARSER_H
