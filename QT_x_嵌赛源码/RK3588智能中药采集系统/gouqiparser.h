#ifndef GOUQIPARSER_H
#define GOUQIPARSER_H

#include "gouqiresult.h"

class GouqiParser
{
public:
    static GouqiRecognitionResult parse(const QString &rawOutput);
    static bool isNotRecognized(const QString &rawOutput);
};

#endif // GOUQIPARSER_H
