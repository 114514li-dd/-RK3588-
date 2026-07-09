#include "buildconfig.h"

QString BuildConfig::cameraBackend()
{
#if defined(HAS_OPENCV)
    return QStringLiteral("OpenCV (USB/V4L2)");
#elif defined(USE_QT_CAMERA)
    return QStringLiteral("Qt Multimedia");
#else
    return QStringLiteral("未编译");
#endif
}

bool BuildConfig::hasCameraSupport()
{
#if defined(HAS_OPENCV) || defined(USE_QT_CAMERA)
    return true;
#else
    return false;
#endif
}
