#include "objectprompt.h"

#include <QFile>
#include <QTemporaryFile>

namespace {
const char kPromptResource[] = ":/prompts/object_recognition.txt";

const char kFixedObjectPrompt[] =
    "你是通用物品识别助手。请仔细观察图片中的主要物体，用中文回答。\n"
    "必须严格按以下格式输出：\n"
    "【物品名称】（具体名称，如：黑色中性笔）\n"
    "【物品类别】（如：文具、电子产品、药材、日用品等）\n"
    "【外观特征】（颜色、形状、材质、尺寸感、可见文字/品牌、摆放状态等，1-3句）\n"
    "【详细描述】（用对话口吻再介绍一遍，2-4句）\n"
    "若无法辨认，输出：\n"
    "【识别失败】请说明原因，并给出拍摄建议。";
}

QString ObjectPrompt::text()
{
    QFile file(QString::fromLatin1(kPromptResource));
    if (file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        const QString content = QString::fromUtf8(file.readAll()).trimmed();
        if (!content.isEmpty()) {
            return content;
        }
    }
    return QString::fromUtf8(kFixedObjectPrompt);
}

QString ObjectPrompt::writeToTempFile()
{
    const QString prompt = text();

    QTemporaryFile tempFile;
    tempFile.setAutoRemove(false);
    if (!tempFile.open()) {
        return QString();
    }

    tempFile.write(prompt.toUtf8());
    tempFile.close();
    return tempFile.fileName();
}
