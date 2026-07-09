#ifndef CAMERATHREAD_H
#define CAMERATHREAD_H

#include <QImage>
#include <QMutex>
#include <QThread>

/**
 * @brief 摄像头采集线程
 * Linux/RK3588: OpenCV 读取 V4L2 (/dev/video0)
 * Windows 调试: Qt Multimedia 读取系统摄像头
 */
class CameraThread : public QThread
{
    Q_OBJECT

public:
    explicit CameraThread(QObject *parent = 0);
    ~CameraThread();

    bool isCameraRunning() const;
    QImage currentFrame() const;
    void publishFrame(const QImage &image);

public slots:
    void startCamera(const QString &devicePath = QStringLiteral("/dev/video0"));
    void stopCamera();

signals:
    void frameReady(const QImage &image);
    void cameraOpened();
    void cameraStopped();
    void cameraError(const QString &message);

protected:
    void run() override;

private:
    mutable QMutex m_mutex;
    QImage m_currentFrame;
    QString m_devicePath;
    volatile bool m_running;
    volatile bool m_stopRequested;
};

#endif // CAMERATHREAD_H
