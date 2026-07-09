#ifndef BUILDCONFIG_H
#define BUILDCONFIG_H

#include <QString>

class BuildConfig
{
public:
    static QString cameraBackend();
    static bool hasCameraSupport();
};

#endif // BUILDCONFIG_H
