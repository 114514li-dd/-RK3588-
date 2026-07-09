#include "camerathread.h"
#include "platformpaths.h"

#ifdef HAS_OPENCV

#include <opencv2/imgproc.hpp>
#include <opencv2/videoio.hpp>

#if defined(__has_include)
#  if __has_include(<opencv2/core/utils/logger.hpp>)
#    include <opencv2/core/utils/logger.hpp>
#    define HAS_OPENCV_LOGGER 1
#  endif
#endif

namespace {

QImage matToQImage(const cv::Mat &mat)
{
    if (mat.empty()) {
        return QImage();
    }

    if (mat.type() == CV_8UC3) {
        cv::Mat rgb;
        cv::cvtColor(mat, rgb, cv::COLOR_BGR2RGB);
        return QImage(rgb.data, rgb.cols, rgb.rows, static_cast<int>(rgb.step),
                      QImage::Format_RGB888)
            .copy();
    }

    if (mat.type() == CV_8UC1) {
        return QImage(mat.data, mat.cols, mat.rows, static_cast<int>(mat.step),
                      QImage::Format_Grayscale8)
            .copy();
    }

    return QImage();
}

bool tryOpenV4L2Device(cv::VideoCapture &capture, const QString &devicePath)
{
    capture.release();
    if (!capture.open(devicePath.toStdString(), cv::CAP_V4L2)) {
        return false;
    }

    cv::Mat probe;
    capture >> probe;
    if (probe.empty()) {
        capture.release();
        return false;
    }
    return true;
}

bool openUsbCamera(cv::VideoCapture &capture, const QString &deviceHint, QString *openedDevice = nullptr)
{
    const QString device = PlatformPaths::resolveCameraDevice(deviceHint);

#ifdef Q_OS_WIN
    bool ok = false;
    const int index = device.toInt(&ok);
    if (ok && index >= 0) {
        if (capture.open(index, cv::CAP_DSHOW)) {
            return true;
        }
        if (capture.open(index, cv::CAP_MSMF)) {
            return true;
        }
        return capture.open(index);
    }
    return capture.open(device.toStdString());
#else
    QStringList candidates;
    candidates << device;
    const QStringList allDevices = PlatformPaths::listVideoDevices();
    for (int i = 0; i < allDevices.size(); ++i) {
        if (!candidates.contains(allDevices.at(i))) {
            candidates << allDevices.at(i);
        }
    }

    bool indexOk = false;
    const int index = device.toInt(&indexOk);
    if (indexOk && index >= 0) {
        const QString indexed = QStringLiteral("/dev/video%1").arg(index);
        if (!candidates.contains(indexed)) {
            candidates.prepend(indexed);
        }
    }

    for (int i = 0; i < candidates.size(); ++i) {
        if (tryOpenV4L2Device(capture, candidates.at(i))) {
            if (openedDevice) {
                *openedDevice = candidates.at(i);
            }
            return true;
        }
    }
    return false;
#endif
}

} // namespace

#endif // HAS_OPENCV

#ifdef USE_QT_CAMERA

#include <QAbstractVideoBuffer>
#include <QAbstractVideoSurface>
#include <QCamera>
#include <QCameraInfo>
#include <QEventLoop>
#include <QTimer>
#include <QVideoFrame>

namespace {

static QImage yuv422ToRgbImage(const uchar *src, int width, int height, int bytesPerLine, bool uyvy)
{
    QImage image(width, height, QImage::Format_RGB888);
    for (int y = 0; y < height; ++y) {
        uchar *dest = image.scanLine(y);
        const uchar *line = src + y * bytesPerLine;
        for (int x = 0; x < width; x += 2) {
            int y0;
            int u;
            int y1;
            int v;
            if (uyvy) {
                y0 = line[1];
                u = line[0] - 128;
                y1 = line[3];
                v = line[2] - 128;
            } else {
                y0 = line[0];
                u = line[1] - 128;
                y1 = line[2];
                v = line[3] - 128;
            }

            const int c0 = qBound(0, y0 + ((359 * v) >> 8), 255);
            const int c1 = qBound(0, y0 - ((88 * u + 183 * v) >> 8), 255);
            const int c2 = qBound(0, y0 + ((454 * u) >> 8), 255);
            const int c3 = qBound(0, y1 + ((359 * v) >> 8), 255);
            const int c4 = qBound(0, y1 - ((88 * u + 183 * v) >> 8), 255);
            const int c5 = qBound(0, y1 + ((454 * u) >> 8), 255);

            dest[x * 3] = static_cast<uchar>(c0);
            dest[x * 3 + 1] = static_cast<uchar>(c1);
            dest[x * 3 + 2] = static_cast<uchar>(c2);
            dest[x * 3 + 3] = static_cast<uchar>(c3);
            dest[x * 3 + 4] = static_cast<uchar>(c4);
            dest[x * 3 + 5] = static_cast<uchar>(c5);
            line += 4;
        }
    }
    return image;
}

// Qt 5.8 无 QVideoFrame::image()，需手动转换（image() 自 Qt 5.15 才有）
static QImage videoFrameToQImage(const QVideoFrame &frame)
{
    QVideoFrame clone(frame);
    if (!clone.map(QAbstractVideoBuffer::ReadOnly)) {
        return QImage();
    }

    QImage image;
    const QVideoFrame::PixelFormat format = clone.pixelFormat();
    const int width = clone.width();
    const int height = clone.height();
    const int bytesPerLine = clone.bytesPerLine();
    const uchar *bits = clone.bits();

    if (format == QVideoFrame::Format_RGB32) {
        image = QImage(bits, width, height, bytesPerLine, QImage::Format_RGB32).copy();
    } else if (format == QVideoFrame::Format_ARGB32) {
        image = QImage(bits, width, height, bytesPerLine, QImage::Format_ARGB32).copy();
    } else if (format == QVideoFrame::Format_YUYV) {
        image = yuv422ToRgbImage(bits, width, height, bytesPerLine, false);
    } else if (format == QVideoFrame::Format_UYVY) {
        image = yuv422ToRgbImage(bits, width, height, bytesPerLine, true);
    }

    clone.unmap();
    return image;
}

class FrameGrabber : public QAbstractVideoSurface
{
public:
    explicit FrameGrabber(CameraThread *thread)
        : m_thread(thread)
    {
    }

    QList<QVideoFrame::PixelFormat> supportedPixelFormats(
        QAbstractVideoBuffer::HandleType handleType = QAbstractVideoBuffer::NoHandle) const Q_DECL_OVERRIDE
    {
        Q_UNUSED(handleType);
        return QList<QVideoFrame::PixelFormat>()
               << QVideoFrame::Format_RGB32
               << QVideoFrame::Format_ARGB32
               << QVideoFrame::Format_YUYV
               << QVideoFrame::Format_UYVY;
    }

    bool present(const QVideoFrame &frame) Q_DECL_OVERRIDE
    {
        const QImage image = videoFrameToQImage(frame);
        if (!image.isNull() && m_thread) {
            m_thread->publishFrame(image);
        }
        return true;
    }

private:
    CameraThread *m_thread;
};

QCameraInfo selectCamera(const QString &deviceHint)
{
    const QList<QCameraInfo> cameras = QCameraInfo::availableCameras();
    if (cameras.isEmpty()) {
        return QCameraInfo();
    }

    if (!deviceHint.isEmpty()) {
        for (int i = 0; i < cameras.size(); ++i) {
            if (cameras.at(i).deviceName().contains(deviceHint, Qt::CaseInsensitive)) {
                return cameras.at(i);
            }
        }
    }

    return QCameraInfo::defaultCamera();
}

} // namespace

#endif // USE_QT_CAMERA

CameraThread::CameraThread(QObject *parent)
    : QThread(parent),
      m_devicePath(PlatformPaths::defaultCameraDevice()),
      m_running(false),
      m_stopRequested(false)
{
}

CameraThread::~CameraThread()
{
    stopCamera();
    wait(3000);
}

bool CameraThread::isCameraRunning() const
{
    return m_running;
}

QImage CameraThread::currentFrame() const
{
    QMutexLocker locker(&m_mutex);
    return m_currentFrame;
}

void CameraThread::publishFrame(const QImage &image)
{
    // 修正摄像头画面上下颠倒，保证人物正常朝向（头在上）
    const QImage corrected = image.mirrored(false, true);

    QMutexLocker locker(&m_mutex);
    m_currentFrame = corrected;
    emit frameReady(corrected);
}

void CameraThread::startCamera(const QString &devicePath)
{
    if (isRunning()) {
        stopCamera();
        wait(3000);
    }

    m_devicePath = devicePath.isEmpty() ? PlatformPaths::defaultCameraDevice() : devicePath;
    m_stopRequested = false;
    start();
}

void CameraThread::stopCamera()
{
    m_stopRequested = true;
}

void CameraThread::run()
{
#ifdef HAS_OPENCV

#ifdef HAS_OPENCV_LOGGER
    cv::utils::logging::setLogLevel(cv::utils::logging::LOG_LEVEL_ERROR);
#endif

    cv::VideoCapture capture;
    const QString resolvedDevice = PlatformPaths::resolveCameraDevice(m_devicePath);
    QString openedDevice;
    if (!openUsbCamera(capture, m_devicePath, &openedDevice)) {
        const QStringList devices = PlatformPaths::listVideoDevices();
        const QString deviceList = devices.isEmpty()
            ? QStringLiteral("（系统未检测到 /dev/video*）")
            : devices.join(QStringLiteral(", "));
        emit cameraError(QStringLiteral("USB 摄像头打开失败（配置: %1）\n\n"
                                         "已扫描设备: %2\n\n"
                                         "Linux 排查：\n"
                                         "  1. ls -l /dev/video*\n"
                                         "  2. v4l2-ctl --list-devices\n"
                                         "  3. 虚拟机: VMware → 可移动设备 → 摄像头 → 连接\n"
                                         "  4. 设置里可改设备路径，如 /dev/video0\n\n"
                                         "无摄像头时可用【打开图片】测试检测与 AI 识物")
                             .arg(resolvedDevice, deviceList));
        return;
    }

    capture.set(cv::CAP_PROP_FRAME_WIDTH, 640);
    capture.set(cv::CAP_PROP_FRAME_HEIGHT, 480);
    capture.set(cv::CAP_PROP_FPS, 30);

    m_running = true;
    emit cameraOpened();

    while (!m_stopRequested) {
        cv::Mat frame;
        capture >> frame;
        if (frame.empty()) {
            msleep(30);
            continue;
        }

        const QImage image = matToQImage(frame);
        if (!image.isNull()) {
            publishFrame(image);
        }

        msleep(33);
    }

    capture.release();
    m_running = false;
    emit cameraStopped();

#elif defined(USE_QT_CAMERA)

    const QCameraInfo cameraInfo = selectCamera(m_devicePath);
    if (cameraInfo.isNull()) {
        emit cameraError(QStringLiteral("未检测到可用摄像头，请确认电脑/板端已连接摄像头驱动"));
        return;
    }

    FrameGrabber grabber(this);
    QCamera camera(cameraInfo);
    camera.setViewfinder(&grabber);
    camera.start();

    if (camera.error() != QCamera::NoError) {
        emit cameraError(QStringLiteral("摄像头打开失败：%1").arg(camera.errorString()));
        return;
    }

    m_running = true;
    emit cameraOpened();

    QEventLoop eventLoop;
    QTimer pollTimer;
    pollTimer.setInterval(50);
    connect(&pollTimer, &QTimer::timeout, [this, &eventLoop]() {
        if (m_stopRequested) {
            eventLoop.quit();
        }
    });
    pollTimer.start();
    eventLoop.exec();
    pollTimer.stop();

    camera.stop();
    m_running = false;
    emit cameraStopped();

#else

    emit cameraError(QStringLiteral(
        "当前编译未启用摄像头模块。\n"
        "请安装 OpenCV 后重新 qmake && make。\n"
        "Windows: 在 .pro 中设置 OPENCV_DIR（推荐，与 ElfBoard USB 摄像头一致）\n"
        "Linux: sudo apt install libopencv-dev"));
    m_running = false;

#endif
}
