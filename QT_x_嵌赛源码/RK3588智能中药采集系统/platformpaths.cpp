#include "platformpaths.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QStandardPaths>
#include <algorithm>

QString PlatformPaths::inferScriptFileName()
{
#ifdef Q_OS_WIN
    return QStringLiteral("deepseek_infer.bat");
#else
    return QStringLiteral("deepseek_infer.sh");
#endif
}

QString PlatformPaths::inferScriptRelativePath()
{
    return QStringLiteral("scripts/") + inferScriptFileName();
}

QString PlatformPaths::normalizePath(const QString &path)
{
    return QDir::cleanPath(QDir::fromNativeSeparators(path.trimmed()));
}

QString PlatformPaths::resolveFromAppDir(const QString &relativePath)
{
    const QString appDir = QCoreApplication::applicationDirPath();
    return normalizePath(QDir(appDir).filePath(relativePath));
}

QString PlatformPaths::resolveInferProgram(const QString &configuredPath)
{
    const QString trimmed = configuredPath.trimmed();
    const QString defaultRelative = inferScriptRelativePath();
    QStringList candidates;

    if (!trimmed.isEmpty()) {
        candidates << normalizePath(trimmed);
        if (!QDir::isAbsolutePath(trimmed)) {
            candidates << resolveFromAppDir(trimmed);
        }
    }

    candidates << resolveFromAppDir(defaultRelative);

    QDir dir(QCoreApplication::applicationDirPath());
    for (int i = 0; i < 6; ++i) {
        candidates << normalizePath(dir.filePath(defaultRelative));
        if (!dir.cdUp()) {
            break;
        }
    }

    for (int i = 0; i < candidates.size(); ++i) {
        if (QFile::exists(candidates.at(i))) {
            return candidates.at(i);
        }
    }

    return trimmed.isEmpty() ? defaultRelative : normalizePath(trimmed);
}

QString PlatformPaths::defaultCameraDevice()
{
#ifdef Q_OS_WIN
    return QStringLiteral("0");
#else
    return QStringLiteral("/dev/video0");
#endif
}

QString PlatformPaths::resolveCameraDevice(const QString &deviceHint)
{
    const QString trimmed = deviceHint.trimmed();
#ifdef Q_OS_WIN
    if (trimmed.isEmpty()) {
        return QStringLiteral("0");
    }
    if (trimmed.startsWith(QStringLiteral("/dev/video"))) {
        bool ok = false;
        const int index = trimmed.mid(10).toInt(&ok);
        if (ok && index >= 0) {
            return QString::number(index);
        }
    }
    return trimmed;
#else
    if (trimmed.isEmpty()) {
        return QStringLiteral("/dev/video0");
    }
    if (trimmed.startsWith(QStringLiteral("/dev/video"))) {
        return trimmed;
    }
    if (trimmed.startsWith(QStringLiteral("video"))) {
        return QStringLiteral("/dev/") + trimmed;
    }
    bool ok = false;
    const int index = trimmed.toInt(&ok);
    if (ok && index >= 0) {
        return QStringLiteral("/dev/video%1").arg(index);
    }
    return trimmed;
#endif
}

QStringList PlatformPaths::listVideoDevices()
{
    QStringList devices;
#ifndef Q_OS_WIN
    const QDir devDir(QStringLiteral("/dev"));
    const QStringList entries = devDir.entryList(
        QStringList() << QStringLiteral("video*"), QDir::System);
    for (int i = 0; i < entries.size(); ++i) {
        devices << QStringLiteral("/dev/") + entries.at(i);
    }
    std::sort(devices.begin(), devices.end(), [](const QString &a, const QString &b) {
        const int na = a.mid(10).toInt();
        const int nb = b.mid(10).toInt();
        return na < nb;
    });
#endif
    return devices;
}

QString PlatformPaths::cameraSettingsHint()
{
#ifdef Q_OS_WIN
    return QStringLiteral("0（USB 摄像头索引，ElfBoard UVC 通常填 0）");
#else
    return QStringLiteral("/dev/video0（USB 摄像头，可用 v4l2-ctl --list-devices 查看）");
#endif
}

QString PlatformPaths::tempCaptureDir()
{
    const QString base = QStandardPaths::writableLocation(QStandardPaths::TempLocation);
    const QString dirPath = QDir(base).filePath(QStringLiteral("drug_recognition"));
    QDir().mkpath(dirPath);
    return dirPath;
}
