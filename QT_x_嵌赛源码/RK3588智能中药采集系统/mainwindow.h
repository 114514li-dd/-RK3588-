#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QImage>
#include <QMainWindow>
#include <QStringList>
#include <QTimer>
#include <QVector>

#include <QPushButton>
#include <QTextEdit>
#include <QtGlobal>

#include "aiinferencethread.h"
#include "gouqiresult.h"
#include "herbdetection.h"
#include "objectrecognitionresult.h"

class CameraThread;
class PreviewLabel;

namespace Ui {
class MainWindow;
}

/**
 * @brief 药物智能识别系统主窗口
 * 横屏布局：顶部标题栏 + 左右分栏主体 + 底部功能栏
 */
class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    enum DeviceState {
        StateIdle = 0,
        StateCameraRunning,
        StateRecognizing,
        StateError
    };

    explicit MainWindow(QWidget *parent = 0);
    ~MainWindow();

private slots:
    void onOpenCameraClicked();
    void onOpenImageClicked();
    void onCaptureClicked();
    void onDetectClicked();
    void onAiRecognizeClicked();
    void onClearResultClicked();
    void onHistoryClicked();
    void onSettingsClicked();
    void onExitClicked();

    void onFrameReady(const QImage &image);
    void onCameraOpened();
    void onCameraStopped();
    void onCameraError(const QString &message);

    void onInferenceStarted();
    void onInferenceFinished(const GouqiRecognitionResult &result);
    void onObjectInferenceFinished(const ObjectRecognitionResult &result);
    void onInferenceFailed(const QString &message);
    void onLiveDetectTick();

private:
    void setupConnections();
    void loadStyleSheet();
    void loadSettings();
    void saveSettings();
    void setDeviceState(DeviceState state);
    void updateStatusLabel();
    void setRecognitionBusy(bool busy);
    void showResult(const GouqiRecognitionResult &result);
    void showDetections(const QVector<HerbDetectItem> &items);
    void showNotRecognizedGuide();
    void handleNotRecognized();
    void runDeepSeekForGouqi(const QImage &image, double confidence);
    void runObjectRecognition(const QImage &image);
    void appendChatMessage(const QString &role, const QString &message);
    void appendHistoryRecord(const QString &drugName, const QString &summary);
    QString captureImagePath() const;
    bool saveCaptureImage(const QImage &image, const QString &filePath) const;
    void openSettingsDialog();
    void openHistoryDialog();
    bool hasWorkingFrame() const;
    QImage workingFrame() const;
    void updateDetectButtons();
    void freezeCameraPreview(const QImage &image);
    void resumeCameraPreview();
    void updateCaptureButtonText();

    Ui::MainWindow *ui;
    PreviewLabel *m_previewLabel;
    QPushButton *m_btnDetect;
    QPushButton *m_btnOpenImage;
    QPushButton *m_btnAiRecognize;
    QTextEdit *m_textEditChat;
    CameraThread *m_cameraThread;
    AIInferenceThread *m_aiThread;
    QTimer *m_liveDetectTimer;
    AIInferenceThread::InferenceMode m_inferenceMode;
    DeviceState m_deviceState;
    QImage m_lastFrame;
    QImage m_capturedImage;
    QString m_capturedImagePath;
    double m_pendingConfidence;
    QVector<HerbDetectItem> m_pendingDetections;
    QString m_cameraDevice;
    QString m_inferProgram;
    QString m_captureDir;
    QStringList m_historyRecords;
    bool m_cameraActive;
    bool m_previewFrozen;
    qint64 m_lastLiveDetectMs;
    QVector<HerbDetectItem> m_lastLiveDetections;
};

#endif // MAINWINDOW_H
