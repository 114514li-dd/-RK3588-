#include "aiinferencethread.h"

#include "gouqiparser.h"
#include "gouqiprompt.h"
#include "nativevisionrecognizer.h"
#include "objectparser.h"
#include "objectprompt.h"
#include "platformpaths.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QImage>
#include <QProcess>

namespace {
const int kInferenceTimeoutMs = 120000;

QString decodeProcessOutput(const QByteArray &data)
{
    if (data.isEmpty()) {
        return QString();
    }

    QString utf8Text = QString::fromUtf8(data).trimmed();
#ifdef Q_OS_WIN
    if (utf8Text.contains(QChar(0xFFFD))) {
        const QString localText = QString::fromLocal8Bit(data).trimmed();
        if (!localText.isEmpty()) {
            return localText;
        }
    }
#endif
    return utf8Text;
}

} // namespace

bool AIInferenceThread::isDemoInferScript(const QString &programPath)
{
    const QString fileName = QFileInfo(programPath).fileName();
    return fileName.compare(PlatformPaths::inferScriptFileName(), Qt::CaseInsensitive) == 0;
}

QString AIInferenceThread::resolveProgramPath(const QString &configuredPath)
{
    return PlatformPaths::resolveInferProgram(configuredPath);
}

bool AIInferenceThread::ensureInferScriptAvailable(const QString &programPath) const
{
    if (QFile::exists(programPath)) {
        return true;
    }

    const QString defaultScript = PlatformPaths::inferScriptRelativePath();
    const QString targetPath = PlatformPaths::resolveFromAppDir(defaultScript);
    const QString pyTarget = PlatformPaths::resolveFromAppDir(QStringLiteral("scripts/object_recognize.py"));

    QDir().mkpath(QFileInfo(targetPath).absolutePath());
    QDir().mkpath(QFileInfo(pyTarget).absolutePath());

    QDir dir(QCoreApplication::applicationDirPath());
    for (int i = 0; i < 6; ++i) {
        const QString sourcePath = dir.filePath(defaultScript);
        if (QFile::exists(sourcePath) && !QFile::exists(targetPath)) {
            QFile::copy(sourcePath, targetPath);
#ifndef Q_OS_WIN
            QFile::setPermissions(targetPath, QFile::ReadOwner | QFile::WriteOwner | QFile::ExeOwner
                                               | QFile::ReadGroup | QFile::ExeGroup
                                               | QFile::ReadOther | QFile::ExeOther);
#endif
        }

        const QString pySource = dir.filePath(QStringLiteral("scripts/object_recognize.py"));
        if (QFile::exists(pySource) && !QFile::exists(pyTarget)) {
            QFile::copy(pySource, pyTarget);
        }

        if (!dir.cdUp()) {
            break;
        }
    }

    return QFile::exists(programPath) || QFile::exists(targetPath);
}

AIInferenceThread::AIInferenceThread(QObject *parent)
    : QThread(parent),
      m_programPath(PlatformPaths::inferScriptRelativePath()),
      m_mode(GouqiMode)
{
}

void AIInferenceThread::setProgramPath(const QString &programPath)
{
    m_programPath = resolveProgramPath(programPath);
}

QString AIInferenceThread::programPath() const
{
    return m_programPath;
}

void AIInferenceThread::startInference(const QString &imagePath, InferenceMode mode)
{
    if (isRunning()) {
        return;
    }

    m_imagePath = PlatformPaths::normalizePath(imagePath);
    m_mode = mode;
    start();
}

void AIInferenceThread::run()
{
    emit inferenceStarted();

    if (m_imagePath.isEmpty() || !QFile::exists(m_imagePath)) {
        emit inferenceFailed(QStringLiteral("抓拍图片不存在，请重新拍摄"));
        return;
    }

    const QImage sourceImage = NativeVisionRecognizer::loadImage(m_imagePath);
    if (sourceImage.isNull()) {
        emit inferenceFailed(QStringLiteral("无法读取图片，请重新拍摄"));
        return;
    }

    const auto finishWithNative = [this, &sourceImage]() {
        if (m_mode == ObjectMode) {
            emit objectInferenceFinished(NativeVisionRecognizer::recognizeObject(sourceImage));
        } else {
            emit inferenceFinished(NativeVisionRecognizer::recognizeGouqi(sourceImage));
        }
    };

    if (m_programPath.isEmpty()) {
        finishWithNative();
        return;
    }

    QString programPath = resolveProgramPath(m_programPath);
    ensureInferScriptAvailable(programPath);
    programPath = resolveProgramPath(m_programPath);

    if (!QFile::exists(programPath) || isDemoInferScript(programPath)) {
        finishWithNative();
        return;
    }

    const QString promptFile = (m_mode == ObjectMode)
                                   ? ObjectPrompt::writeToTempFile()
                                   : GouqiPrompt::writeToTempFile();
    if (promptFile.isEmpty()) {
        finishWithNative();
        return;
    }

    const QString modeArg = (m_mode == ObjectMode) ? QStringLiteral("object") : QStringLiteral("gouqi");
    const QStringList inferArgs = QStringList()
                                  << QStringLiteral("--image") << m_imagePath
                                  << QStringLiteral("--prompt-file") << PlatformPaths::normalizePath(promptFile)
                                  << QStringLiteral("--mode") << modeArg;

    QProcess process;
#ifdef Q_OS_WIN
    if (programPath.endsWith(QStringLiteral(".bat"), Qt::CaseInsensitive)
        || programPath.endsWith(QStringLiteral(".cmd"), Qt::CaseInsensitive)) {
        QStringList cmdArgs;
        cmdArgs << QStringLiteral("/C") << QDir::toNativeSeparators(programPath);
        cmdArgs << inferArgs;
        process.setProgram(QStringLiteral("cmd.exe"));
        process.setArguments(cmdArgs);
    } else {
        process.setProgram(programPath);
        process.setArguments(inferArgs);
    }
#else
    if (programPath.endsWith(QStringLiteral(".sh"), Qt::CaseInsensitive)) {
        process.setProgram(QStringLiteral("/bin/bash"));
        QStringList bashArgs;
        bashArgs << programPath << inferArgs;
        process.setArguments(bashArgs);
    } else {
        process.setProgram(programPath);
        process.setArguments(inferArgs);
    }
#endif

    process.start();
    if (!process.waitForStarted(5000)) {
        QFile::remove(promptFile);
        finishWithNative();
        return;
    }

    if (!process.waitForFinished(kInferenceTimeoutMs)) {
        process.kill();
        process.waitForFinished(3000);
        QFile::remove(promptFile);
        finishWithNative();
        return;
    }

    QFile::remove(promptFile);

    const QString stdoutText = decodeProcessOutput(process.readAllStandardOutput());
    const QString stderrText = decodeProcessOutput(process.readAllStandardError());

    if (process.exitStatus() != QProcess::NormalExit || process.exitCode() != 0 || stdoutText.isEmpty()) {
        Q_UNUSED(stderrText);
        finishWithNative();
        return;
    }

    if (m_mode == ObjectMode) {
        ObjectRecognitionResult objectResult = ObjectParser::parse(stdoutText);
        if (!objectResult.success) {
            finishWithNative();
            return;
        }
        emit objectInferenceFinished(objectResult);
    } else {
        GouqiRecognitionResult gouqiResult = GouqiParser::parse(stdoutText);
        if (!gouqiResult.recognized) {
            finishWithNative();
            return;
        }
        emit inferenceFinished(gouqiResult);
    }
}
