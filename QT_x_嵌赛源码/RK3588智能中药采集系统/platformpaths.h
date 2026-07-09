#ifndef PLATFORMPATHS_H
#define PLATFORMPATHS_H

#include <QString>
#include <QStringList>

/**
 * @brief 跨平台路径与默认配置
 */
class PlatformPaths
{
public:
    static QString inferScriptFileName();
    static QString inferScriptRelativePath();
    static QString resolveFromAppDir(const QString &relativePath);
    static QString resolveInferProgram(const QString &configuredPath);
    static QString defaultCameraDevice();
    static QString resolveCameraDevice(const QString &deviceHint);
    static QStringList listVideoDevices();
    static QString cameraSettingsHint();
    static QString normalizePath(const QString &path);
    static QString tempCaptureDir();
};

#endif // PLATFORMPATHS_H
