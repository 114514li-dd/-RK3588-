#ifndef GOUQIPROMPT_H
#define GOUQIPROMPT_H

#include <QString>
#include <QStringList>

/**
 * @brief 枸杞专用 DeepSeek 识别提示词
 * 固定 prompt，与抓拍图片路径一并传给推理程序。
 */
class GouqiPrompt
{
public:
    static QString text();
    static QString writeToTempFile();
    static QStringList buildInferArguments(const QString &imagePath);
};

#endif // GOUQIPROMPT_H
