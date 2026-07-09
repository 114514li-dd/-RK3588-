#include "mainwindow.h"
#include "ui_mainwindow.h"

#include "aiinferencethread.h"
#include "buildconfig.h"
#include "camerathread.h"
#include "herbdetection.h"
#include "imagepreprocessor.h"
#include "objectrecognitionresult.h"
#include "platformpaths.h"
#include "previewlabel.h"

#include <QApplication>
#include <QDateTime>
#include <QDialog>
#include <QDialogButtonBox>
#include <QDir>
#include <QFile>
#include <QFileDialog>
#include <QFormLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QMessageBox>
#include <QPixmap>
#include <QPushButton>
#include <QSettings>
#include <QVBoxLayout>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent),
      ui(new Ui::MainWindow),
      m_previewLabel(0),
      m_btnDetect(0),
      m_btnOpenImage(0),
      m_btnAiRecognize(0),
      m_textEditChat(0),
      m_cameraThread(new CameraThread(this)),
      m_aiThread(new AIInferenceThread(this)),
      m_inferenceMode(AIInferenceThread::GouqiMode),
      m_deviceState(StateIdle),
      m_capturedImagePath(),
      m_pendingConfidence(0.0),
      m_cameraDevice(PlatformPaths::defaultCameraDevice()),
      m_inferProgram(PlatformPaths::inferScriptRelativePath()),
      m_captureDir(PlatformPaths::tempCaptureDir()),
      m_cameraActive(false),
      m_previewFrozen(false),
      m_lastLiveDetectMs(0)
{
    ui->setupUi(this);

    m_liveDetectTimer = new QTimer(this);
    m_liveDetectTimer->setInterval(350);
    connect(m_liveDetectTimer, SIGNAL(timeout()), this, SLOT(onLiveDetectTick()));

    ui->labelTitle->setText(QStringLiteral("中药材智能识别系统"));
    setWindowTitle(QStringLiteral("中药材智能识别系统"));

    const int previewIndex = ui->leftPanelLayout->indexOf(ui->labelPreview);
    ui->leftPanelLayout->removeWidget(ui->labelPreview);
    ui->labelPreview->hide();
    m_previewLabel = new PreviewLabel(ui->leftPanel);
    ui->leftPanelLayout->insertWidget(previewIndex, m_previewLabel);

    ui->btnCapture->setText(QStringLiteral("拍照"));
    m_btnOpenImage = new QPushButton(QStringLiteral("打开图片"), ui->leftPanel);
    m_btnOpenImage->setObjectName(QStringLiteral("secondaryButton"));
    m_btnOpenImage->setMinimumHeight(45);
    m_btnDetect = new QPushButton(QStringLiteral("检测"), ui->leftPanel);
    m_btnDetect->setObjectName(QStringLiteral("primaryButton"));
    m_btnDetect->setMinimumHeight(45);
    m_btnDetect->setEnabled(false);
    ui->leftButtonLayout->insertWidget(1, m_btnOpenImage);
    ui->leftButtonLayout->insertWidget(3, m_btnDetect);
    m_btnAiRecognize = new QPushButton(QStringLiteral("AI识物"), ui->leftPanel);
    m_btnAiRecognize->setObjectName(QStringLiteral("primaryButton"));
    m_btnAiRecognize->setMinimumHeight(45);
    m_btnAiRecognize->setEnabled(false);
    ui->leftButtonLayout->insertWidget(4, m_btnAiRecognize);

    m_textEditChat = new QTextEdit(ui->rightPanel);
    m_textEditChat->setObjectName(QStringLiteral("textEditChat"));
    m_textEditChat->setReadOnly(true);
    m_textEditChat->setPlaceholderText(QStringLiteral("AI 识物对话将显示在这里..."));
    m_textEditChat->setMinimumHeight(160);
    ui->rightPanelLayout->insertWidget(0, new QLabel(QStringLiteral("AI 识物对话"), ui->rightPanel));
    ui->rightPanelLayout->insertWidget(1, m_textEditChat);

    ui->labelDetailTitle->setText(QStringLiteral("药材检测结果 / 功效 / 用法 / 禁忌"));

    ui->mainSplitLayout->setStretch(0, 58);
    ui->mainSplitLayout->setStretch(1, 42);

    loadStyleSheet();
    loadSettings();
    setupConnections();
    setDeviceState(StateIdle);

    if (!BuildConfig::hasCameraSupport()) {
        ui->labelStatus->setToolTip(QStringLiteral("当前版本未编译摄像头，请重新 qmake 并编译"));
    } else {
        ui->labelStatus->setToolTip(
            QStringLiteral("摄像头驱动: %1").arg(BuildConfig::cameraBackend()));
    }
}

MainWindow::~MainWindow()
{
    saveSettings();
    m_cameraThread->stopCamera();
    m_cameraThread->wait(3000);
    delete ui;
}

void MainWindow::setupConnections()
{
    connect(ui->btnOpenCamera, SIGNAL(clicked()), this, SLOT(onOpenCameraClicked()));
    connect(m_btnOpenImage, SIGNAL(clicked()), this, SLOT(onOpenImageClicked()));
    connect(ui->btnCapture, SIGNAL(clicked()), this, SLOT(onCaptureClicked()));
    connect(m_btnDetect, SIGNAL(clicked()), this, SLOT(onDetectClicked()));
    connect(m_btnAiRecognize, SIGNAL(clicked()), this, SLOT(onAiRecognizeClicked()));
    connect(ui->btnClearResult, SIGNAL(clicked()), this, SLOT(onClearResultClicked()));
    connect(ui->btnHistory, SIGNAL(clicked()), this, SLOT(onHistoryClicked()));
    connect(ui->btnSettings, SIGNAL(clicked()), this, SLOT(onSettingsClicked()));
    connect(ui->btnExit, SIGNAL(clicked()), this, SLOT(onExitClicked()));

    connect(m_cameraThread, SIGNAL(frameReady(QImage)), this, SLOT(onFrameReady(QImage)));
    connect(m_cameraThread, SIGNAL(cameraOpened()), this, SLOT(onCameraOpened()));
    connect(m_cameraThread, SIGNAL(cameraStopped()), this, SLOT(onCameraStopped()));
    connect(m_cameraThread, SIGNAL(cameraError(QString)), this, SLOT(onCameraError(QString)));

    connect(m_aiThread, SIGNAL(inferenceStarted()), this, SLOT(onInferenceStarted()));
    connect(m_aiThread, SIGNAL(inferenceFinished(GouqiRecognitionResult)),
            this, SLOT(onInferenceFinished(GouqiRecognitionResult)));
    connect(m_aiThread, SIGNAL(objectInferenceFinished(ObjectRecognitionResult)),
            this, SLOT(onObjectInferenceFinished(ObjectRecognitionResult)));
    connect(m_aiThread, SIGNAL(inferenceFailed(QString)), this, SLOT(onInferenceFailed(QString)));
}

void MainWindow::loadStyleSheet()
{
    QFile styleFile(QStringLiteral(":/style/style.qss"));
    if (styleFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
        qApp->setStyleSheet(QString::fromUtf8(styleFile.readAll()));
    }
}

void MainWindow::loadSettings()
{
    QSettings settings;
    const QString defaultProgram = PlatformPaths::inferScriptRelativePath();

    QString savedProgram = settings.value(QStringLiteral("ai/program"), defaultProgram).toString();
    if (savedProgram == QStringLiteral("./deepseek_infer")
        || savedProgram == QStringLiteral("deepseek_infer")) {
        savedProgram = defaultProgram;
    }

    m_cameraDevice = settings.value(QStringLiteral("camera/device"), PlatformPaths::defaultCameraDevice()).toString();
    m_inferProgram = AIInferenceThread::resolveProgramPath(savedProgram);
    m_captureDir = settings.value(QStringLiteral("capture/dir"), PlatformPaths::tempCaptureDir()).toString();
    m_historyRecords = settings.value(QStringLiteral("history/records")).toStringList();
    m_aiThread->setProgramPath(m_inferProgram);
}

void MainWindow::saveSettings()
{
    QSettings settings;
    settings.setValue(QStringLiteral("camera/device"), m_cameraDevice);
    settings.setValue(QStringLiteral("ai/program"), m_inferProgram);
    settings.setValue(QStringLiteral("capture/dir"), m_captureDir);
    settings.setValue(QStringLiteral("history/records"), m_historyRecords);
}

void MainWindow::setDeviceState(DeviceState state)
{
    m_deviceState = state;
    updateStatusLabel();
    updateDetectButtons();
}

void MainWindow::updateStatusLabel()
{
    QString statusText;
    switch (m_deviceState) {
    case StateIdle:
        statusText = QStringLiteral("设备状态：空闲");
        break;
    case StateCameraRunning:
        statusText = QStringLiteral("设备状态：摄像中");
        break;
    case StateRecognizing:
        statusText = QStringLiteral("设备状态：识别中");
        break;
    case StateError:
        statusText = QStringLiteral("设备状态：异常");
        break;
    }

    ui->labelStatus->setText(statusText);
}

void MainWindow::setRecognitionBusy(bool busy)
{
    ui->btnOpenCamera->setEnabled(!busy);
    ui->btnCapture->setEnabled(!busy && m_cameraActive);
    m_btnOpenImage->setEnabled(!busy);
    updateDetectButtons();
    ui->btnClearResult->setEnabled(!busy);
    ui->btnHistory->setEnabled(!busy);
    ui->btnSettings->setEnabled(!busy);
    ui->btnExit->setEnabled(!busy);
}

bool MainWindow::hasWorkingFrame() const
{
    if (!m_capturedImage.isNull()) {
        return true;
    }
    return m_cameraActive && !m_lastFrame.isNull();
}

QImage MainWindow::workingFrame() const
{
    if (!m_capturedImage.isNull()) {
        return m_capturedImage;
    }
    if (!m_lastFrame.isNull()) {
        return m_lastFrame;
    }
    return m_cameraThread->currentFrame();
}

void MainWindow::updateDetectButtons()
{
    const bool enabled = m_deviceState != StateRecognizing && hasWorkingFrame();
    m_btnDetect->setEnabled(enabled);
    m_btnAiRecognize->setEnabled(enabled);
}

void MainWindow::showDetections(const QVector<HerbDetectItem> &items)
{
    m_previewLabel->setDetections(items);
}

void MainWindow::showResult(const GouqiRecognitionResult &result)
{
    ui->labelDrugName->setText(result.drugName.isEmpty() ? QStringLiteral("--") : result.drugName);
    ui->labelCategory->setText(result.category.isEmpty() ? QStringLiteral("--") : result.category);

    QStringList lines;
    if (result.confidence > 0.0) {
        lines << QStringLiteral("【置信度】%1").arg(QString::number(result.confidence, 'f', 2));
    }
    lines << result.detailText();
    ui->textEditResult->setPlainText(lines.join(QLatin1Char('\n')));
}

void MainWindow::handleNotRecognized()
{
    m_pendingDetections.clear();
    m_previewLabel->clearDetections();
    showNotRecognizedGuide();
    setDeviceState(m_cameraActive ? StateCameraRunning : StateIdle);
    setRecognitionBusy(false);
}

void MainWindow::appendChatMessage(const QString &role, const QString &message)
{
    const QString timeText = QDateTime::currentDateTime().toString(QStringLiteral("hh:mm:ss"));
    const QString block = QStringLiteral("【%1 %2】\n%3").arg(role, timeText, message.trimmed());
    if (m_textEditChat->toPlainText().isEmpty()) {
        m_textEditChat->setPlainText(block);
    } else {
        m_textEditChat->append(QString());
        m_textEditChat->append(block);
    }
}

void MainWindow::runObjectRecognition(const QImage &image)
{
    const ImagePreprocessor::Result prep = ImagePreprocessor::processAndSaveFullFrame(image);
    if (!prep.success) {
        QMessageBox::warning(this, QStringLiteral("预处理失败"), prep.errorMessage);
        setDeviceState(StateError);
        return;
    }

    m_capturedImagePath = prep.savedPath;
    m_inferenceMode = AIInferenceThread::ObjectMode;
    setDeviceState(StateRecognizing);
    setRecognitionBusy(true);
    appendChatMessage(QStringLiteral("用户"), QStringLiteral("请识别图片中的物品，并描述它是什么、外观特征。"));
    appendChatMessage(QStringLiteral("AI"), QStringLiteral("正在分析图片，请稍候..."));
    m_aiThread->startInference(prep.savedPath, AIInferenceThread::ObjectMode);
}

void MainWindow::runDeepSeekForGouqi(const QImage &image, double confidence)
{
    Q_UNUSED(confidence);

    const ImagePreprocessor::Result prep = ImagePreprocessor::processAndSave(image);
    if (!prep.success) {
        QMessageBox::warning(this, QStringLiteral("预处理失败"), prep.errorMessage);
        setDeviceState(StateError);
        return;
    }

    m_capturedImagePath = prep.savedPath;
    m_inferenceMode = AIInferenceThread::GouqiMode;
    setDeviceState(StateRecognizing);
    setRecognitionBusy(true);
    ui->labelDrugName->setText(QStringLiteral("识别中药材中"));
    ui->labelCategory->setText(QStringLiteral("--"));
    ui->textEditResult->setPlainText(QStringLiteral("正在调用 DeepSeek 分析中药材，请稍候..."));
    m_aiThread->startInference(prep.savedPath);
}

void MainWindow::showNotRecognizedGuide()
{
    ui->labelDrugName->setText(QStringLiteral("未识别到中药材"));
    ui->labelCategory->setText(QStringLiteral("--"));
    ui->textEditResult->setPlainText(QStringLiteral("请重新拍摄，确保中药材占画面中心、光线充足、距离 15~30cm"));

    QMessageBox::information(
        this,
        QStringLiteral("未识别到枸杞"),
        QStringLiteral(
            "未能识别画面中的中药材，请按以下建议调整后重试：\n\n"
            "1. 角度：将中药材置于画面正中央，尽量占满中心区域\n"
            "2. 背景：使用纯色、干净的背景，避免杂物干扰\n"
            "3. 光线：保证充足均匀照明，避免逆光、强反光和阴影\n"
            "4. 距离：靠近一些，确保中药材纹理和颜色清晰可见\n"
            "5. 若枸杞在手机屏/小区域中，可先点【AI识物】，或直接拍摄实物中药材"));
}

QString MainWindow::captureImagePath() const
{
    QDir dir(m_captureDir);
    if (!dir.exists()) {
        dir.mkpath(QStringLiteral("."));
    }

    const QString fileName = QStringLiteral("capture_%1.jpg")
                                 .arg(QDateTime::currentDateTime().toString(QStringLiteral("yyyyMMdd_hhmmss")));
    return dir.filePath(fileName);
}

bool MainWindow::saveCaptureImage(const QImage &image, const QString &filePath) const
{
    if (image.isNull()) {
        return false;
    }
    return image.save(filePath, "JPG", 90);
}

void MainWindow::appendHistoryRecord(const QString &drugName, const QString &summary)
{
    const QString record = QStringLiteral("[%1] %2 - %3")
                               .arg(QDateTime::currentDateTime().toString(QStringLiteral("yyyy-MM-dd hh:mm:ss")))
                               .arg(drugName)
                               .arg(summary.left(40));
    m_historyRecords.prepend(record);
    while (m_historyRecords.size() > 100) {
        m_historyRecords.removeLast();
    }
    saveSettings();
}

void MainWindow::onOpenCameraClicked()
{
    if (m_deviceState == StateRecognizing) {
        return;
    }

    if (!BuildConfig::hasCameraSupport()) {
        QMessageBox::warning(
            this,
            QStringLiteral("摄像头未启用"),
            QStringLiteral(
                "当前程序编译时未包含摄像头模块（驱动: %1）。\n\n"
                "Linux 请在终端执行：\n"
                "  sudo apt install libopencv-dev pkg-config\n"
                "  bash scripts/fix_camera_linux.sh\n\n"
                "注意：脚本必须用 bash 运行，不要用 sh\n"
                "或在 Qt Creator：构建 → 运行 qmake → 重新构建\n\n"
                "qmake 输出应包含 “Linux: OpenCV camera enabled”")
                .arg(BuildConfig::cameraBackend()));
        return;
    }

    if (m_cameraActive) {
        m_cameraThread->stopCamera();
        return;
    }

    m_cameraThread->startCamera(m_cameraDevice);
}

void MainWindow::onOpenImageClicked()
{
    if (m_deviceState == StateRecognizing) {
        return;
    }

    const QString path = QFileDialog::getOpenFileName(
        this,
        QStringLiteral("打开图片"),
        QString(),
        QStringLiteral("图片 (*.png *.jpg *.jpeg *.bmp)"));
    if (path.isEmpty()) {
        return;
    }

    QImage image(path);
    if (image.isNull()) {
        QMessageBox::warning(this, QStringLiteral("错误"), QStringLiteral("无法加载图片"));
        return;
    }

    m_capturedImagePath = path;
    m_previewLabel->clearDetections();
    freezeCameraPreview(image);
    ui->labelDrugName->setText(QStringLiteral("--"));
    ui->labelCategory->setText(QStringLiteral("--"));
    ui->textEditResult->setPlainText(QStringLiteral("图片已加载。点击【检测】识别中药材，或点击【AI识物】描述图中物品。"));
    setDeviceState(m_cameraActive ? StateCameraRunning : StateIdle);
}

void MainWindow::freezeCameraPreview(const QImage &image)
{
    m_capturedImage = image;
    m_previewFrozen = true;
    m_lastFrame = image;
    m_previewLabel->setPixmap(QPixmap::fromImage(image));
    updateCaptureButtonText();
    updateDetectButtons();
}

void MainWindow::resumeCameraPreview()
{
    m_capturedImage = QImage();
    if (m_capturedImagePath.startsWith(m_captureDir)) {
        QFile::remove(m_capturedImagePath);
    }
    m_capturedImagePath.clear();
    m_previewFrozen = false;
    m_lastLiveDetectMs = 0;
    m_lastLiveDetections.clear();
    m_pendingDetections.clear();
    m_previewLabel->clearDetections();

    if (m_cameraActive) {
        const QImage frame = m_cameraThread->currentFrame();
        if (!frame.isNull()) {
            m_lastFrame = frame;
            m_previewLabel->setPixmap(QPixmap::fromImage(frame));
        }
    }

    ui->labelDrugName->setText(QStringLiteral("--"));
    ui->labelCategory->setText(QStringLiteral("--"));
    ui->textEditResult->setPlainText(QString());
    updateCaptureButtonText();
    updateDetectButtons();
}

void MainWindow::updateCaptureButtonText()
{
    if (!m_cameraActive) {
        ui->btnCapture->setText(QStringLiteral("拍照"));
        return;
    }
    ui->btnCapture->setText(m_previewFrozen ? QStringLiteral("继续摄像") : QStringLiteral("拍照"));
}

void MainWindow::onCaptureClicked()
{
    if (!m_cameraActive || m_deviceState == StateRecognizing) {
        return;
    }

    if (m_previewFrozen) {
        resumeCameraPreview();
        ui->textEditResult->setPlainText(QStringLiteral("已恢复实时画面，可重新对准中药材后点击【拍照】。"));
        setDeviceState(StateCameraRunning);
        return;
    }

    const QImage frame = m_cameraThread->currentFrame();
    if (frame.isNull()) {
        QMessageBox::warning(this, QStringLiteral("拍照失败"), QStringLiteral("当前无可用画面，请确认摄像头正常工作"));
        setDeviceState(StateError);
        return;
    }

    m_capturedImagePath.clear();
    m_previewLabel->clearDetections();
    freezeCameraPreview(frame);
    ui->labelDrugName->setText(QStringLiteral("--"));
    ui->labelCategory->setText(QStringLiteral("--"));
    ui->textEditResult->setPlainText(QStringLiteral("照片已拍摄。再次点击【继续摄像】恢复预览，或点击【检测】识别中药材。"));
    setDeviceState(StateCameraRunning);
}

void MainWindow::onDetectClicked()
{
    if (m_deviceState == StateRecognizing) {
        return;
    }

    const QImage frame = workingFrame();
    if (frame.isNull()) {
        QMessageBox::warning(this, QStringLiteral("无法检测"),
                             QStringLiteral("请先开启摄像头或打开/拍摄一张图片"));
        return;
    }

    const HerbDetectResult detectResult = HerbDetector::detect(frame, m_capturedImagePath);
    if (!detectResult.success) {
        QMessageBox::warning(this, QStringLiteral("检测失败"), detectResult.errorMessage);
        return;
    }

    m_previewLabel->clearDetections();

    const HerbDetectItem gouqi = detectResult.bestGouqi();
    if (gouqi.name.isEmpty() || gouqi.confidence < 0.50) {
        handleNotRecognized();
        return;
    }

    m_pendingDetections = detectResult.items;

    QImage target = frame;
    if (gouqi.bbox.isValid()) {
        target = frame.copy(gouqi.bbox);
    }

    m_pendingConfidence = gouqi.confidence;
    runDeepSeekForGouqi(target, gouqi.confidence);
}

void MainWindow::onAiRecognizeClicked()
{
    if (m_deviceState == StateRecognizing) {
        return;
    }

    const QImage frame = workingFrame();
    if (frame.isNull()) {
        QMessageBox::warning(this, QStringLiteral("无法识物"),
                             QStringLiteral("请先开启摄像头或打开/拍摄一张图片"));
        return;
    }

    m_previewLabel->clearDetections();
    runObjectRecognition(frame);
}

void MainWindow::onClearResultClicked()
{
    if (m_deviceState == StateRecognizing) {
        return;
    }

    ui->labelDrugName->setText(QStringLiteral("--"));
    ui->labelCategory->setText(QStringLiteral("--"));
    ui->textEditResult->setPlainText(QString());
    if (m_cameraActive) {
        setDeviceState(StateCameraRunning);
    } else {
        setDeviceState(StateIdle);
    }
}

void MainWindow::onHistoryClicked()
{
    openHistoryDialog();
}

void MainWindow::onSettingsClicked()
{
    if (m_deviceState == StateRecognizing) {
        return;
    }
    openSettingsDialog();
}

void MainWindow::onExitClicked()
{
    const QMessageBox::StandardButton reply = QMessageBox::question(
        this,
        QStringLiteral("退出系统"),
        QStringLiteral("确定要退出药物智能识别系统吗？"),
        QMessageBox::Yes | QMessageBox::No,
        QMessageBox::No);

    if (reply == QMessageBox::Yes) {
        m_cameraThread->stopCamera();
        m_cameraThread->wait(3000);
        qApp->quit();
    }
}

void MainWindow::onFrameReady(const QImage &image)
{
    if (m_deviceState != StateRecognizing && !m_previewFrozen) {
        m_lastFrame = image;
        m_previewLabel->setPixmap(QPixmap::fromImage(image));
        updateDetectButtons();
    }
}

void MainWindow::onLiveDetectTick()
{
    if (!m_cameraActive || m_previewFrozen || m_deviceState == StateRecognizing) {
        return;
    }

    static const double kLiveHideConfidence = 0.34;
    static const int kLiveDetectIntervalMs = 350;
    static const int kLiveClearDelayMs = static_cast<int>(kLiveDetectIntervalMs * 1.5); // 1.5 帧 ≈ 525ms

    const qint64 nowMs = QDateTime::currentMSecsSinceEpoch();

    auto keepOrClearLastDetections = [this, nowMs, kLiveClearDelayMs]() {
        if (m_lastLiveDetections.isEmpty()) {
            m_previewLabel->clearDetections();
            return;
        }
        if (nowMs - m_lastLiveDetectMs >= kLiveClearDelayMs) {
            m_lastLiveDetections.clear();
            m_previewLabel->clearDetections();
        } else {
            showDetections(m_lastLiveDetections);
        }
    };

    const QImage frame = m_cameraThread->currentFrame();
    if (frame.isNull()) {
        keepOrClearLastDetections();
        return;
    }

    const HerbDetectResult detectResult = HerbDetector::detect(frame, QString());
    const HerbDetectItem gouqi = detectResult.bestGouqi();
    const bool hasDetection = detectResult.success
                              && !gouqi.name.isEmpty()
                              && gouqi.confidence >= kLiveHideConfidence;

    if (hasDetection) {
        m_lastLiveDetectMs = nowMs;
        m_lastLiveDetections = detectResult.items;
        showDetections(detectResult.items);
        return;
    }

    keepOrClearLastDetections();
}

void MainWindow::onCameraOpened()
{
    m_cameraActive = true;
    m_previewFrozen = false;
    ui->btnOpenCamera->setText(QStringLiteral("关闭摄像头"));
    ui->btnCapture->setEnabled(true);
    updateCaptureButtonText();
    m_liveDetectTimer->start();
    m_lastLiveDetectMs = 0;
    m_lastLiveDetections.clear();
    updateDetectButtons();
    setDeviceState(StateCameraRunning);
}

void MainWindow::onCameraStopped()
{
    m_cameraActive = false;
    m_liveDetectTimer->stop();
    m_lastLiveDetectMs = 0;
    m_lastLiveDetections.clear();
    m_previewLabel->clearDetections();
    ui->btnOpenCamera->setText(QStringLiteral("开启摄像头"));
    ui->btnCapture->setEnabled(false);
    ui->btnCapture->setText(QStringLiteral("拍照"));
    updateDetectButtons();
    if (m_deviceState != StateRecognizing) {
        setDeviceState(StateIdle);
    }
}

void MainWindow::onCameraError(const QString &message)
{
    m_cameraActive = false;
    ui->btnOpenCamera->setText(QStringLiteral("开启摄像头"));
    ui->btnCapture->setEnabled(false);
    setDeviceState(StateError);
    QMessageBox::critical(this, QStringLiteral("摄像头异常"), message);
}

void MainWindow::onInferenceStarted()
{
    setDeviceState(StateRecognizing);
    setRecognitionBusy(true);
    if (m_inferenceMode == AIInferenceThread::GouqiMode) {
        ui->labelDrugName->setText(QStringLiteral("识别中"));
        ui->labelCategory->setText(QStringLiteral("--"));
        ui->textEditResult->setPlainText(QStringLiteral("正在识别中药材中，请稍候..."));
    }
}

void MainWindow::onObjectInferenceFinished(const ObjectRecognitionResult &result)
{
    QString chatBody;
    if (result.success) {
        chatBody = result.chatText();
        if (!result.objectName.contains(QStringLiteral("枸杞"))) {
            ui->labelDrugName->setText(result.objectName.isEmpty() ? QStringLiteral("--") : result.objectName);
            ui->labelCategory->setText(result.category.isEmpty() ? QStringLiteral("--") : result.category);
            ui->textEditResult->setPlainText(result.appearance.isEmpty() ? result.description : result.appearance);
        } else {
            ui->labelDrugName->setText(QStringLiteral("--"));
            ui->labelCategory->setText(QStringLiteral("--"));
            ui->textEditResult->setPlainText(QString());
        }
        if (!result.objectName.isEmpty() && !result.objectName.contains(QStringLiteral("未能"))) {
            appendHistoryRecord(result.objectName, result.appearance.left(40));
        }
    } else {
        chatBody = result.rawOutput.isEmpty() ? QStringLiteral("未能识别物品，请调整角度与光线后重试。") : result.rawOutput;
    }

    appendChatMessage(QStringLiteral("AI"), chatBody);
    m_inferenceMode = AIInferenceThread::GouqiMode;
    setDeviceState(m_cameraActive ? StateCameraRunning : StateIdle);
    setRecognitionBusy(false);
}

void MainWindow::onInferenceFinished(const GouqiRecognitionResult &result)
{
    if (!result.recognized) {
        setRecognitionBusy(false);
        handleNotRecognized();
        return;
    }

    if (m_previewFrozen) {
        showDetections(m_pendingDetections);
    } else {
        m_previewLabel->clearDetections();
    }
    GouqiRecognitionResult displayResult = result;
    displayResult.confidence = m_pendingConfidence;
    showResult(displayResult);
    appendHistoryRecord(displayResult.drugName, displayResult.detailText());
    m_pendingConfidence = 0.0;
    m_pendingDetections.clear();
    m_inferenceMode = AIInferenceThread::GouqiMode;
    setDeviceState(m_cameraActive ? StateCameraRunning : StateIdle);
    setRecognitionBusy(false);
}

void MainWindow::onInferenceFailed(const QString &message)
{
    if (m_inferenceMode == AIInferenceThread::ObjectMode) {
        appendChatMessage(QStringLiteral("AI"), message);
    } else {
        m_pendingDetections.clear();
        m_previewLabel->clearDetections();
        ui->textEditResult->setPlainText(message);
    }
    m_inferenceMode = AIInferenceThread::GouqiMode;
    setDeviceState(StateError);
    QMessageBox::warning(this, QStringLiteral("识别失败"), message);
    if (m_cameraActive) {
        setDeviceState(StateCameraRunning);
    }
    setRecognitionBusy(false);
}

void MainWindow::openSettingsDialog()
{
    QDialog dialog(this);
    dialog.setWindowTitle(QStringLiteral("系统设置"));
    dialog.setMinimumWidth(520);

    QFormLayout *formLayout = new QFormLayout();
    QLineEdit *deviceEdit = new QLineEdit(m_cameraDevice, &dialog);
    deviceEdit->setPlaceholderText(PlatformPaths::cameraSettingsHint());
    QLineEdit *programEdit = new QLineEdit(m_inferProgram, &dialog);
    QLineEdit *captureDirEdit = new QLineEdit(m_captureDir, &dialog);
    QPushButton *browseProgramBtn = new QPushButton(QStringLiteral("浏览"), &dialog);
    QPushButton *browseDirBtn = new QPushButton(QStringLiteral("浏览"), &dialog);

    QHBoxLayout *programLayout = new QHBoxLayout();
    programLayout->addWidget(programEdit);
    programLayout->addWidget(browseProgramBtn);

    QHBoxLayout *dirLayout = new QHBoxLayout();
    dirLayout->addWidget(captureDirEdit);
    dirLayout->addWidget(browseDirBtn);

    formLayout->addRow(QStringLiteral("摄像头设备"), deviceEdit);
    formLayout->addRow(QStringLiteral("推理程序"), programLayout);
    formLayout->addRow(QStringLiteral("抓拍目录"), dirLayout);

    QDialogButtonBox *buttonBox = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel, &dialog);
    QVBoxLayout *rootLayout = new QVBoxLayout(&dialog);
    rootLayout->addLayout(formLayout);
    rootLayout->addWidget(buttonBox);

    connect(browseProgramBtn, &QPushButton::clicked, [&dialog, programEdit]() {
        const QString path = QFileDialog::getOpenFileName(&dialog, QStringLiteral("选择 DeepSeek 推理程序"));
        if (!path.isEmpty()) {
            programEdit->setText(path);
        }
    });

    connect(browseDirBtn, &QPushButton::clicked, [&dialog, captureDirEdit]() {
        const QString path = QFileDialog::getExistingDirectory(&dialog, QStringLiteral("选择抓拍保存目录"));
        if (!path.isEmpty()) {
            captureDirEdit->setText(path);
        }
    });

    connect(buttonBox, SIGNAL(accepted()), &dialog, SLOT(accept()));
    connect(buttonBox, SIGNAL(rejected()), &dialog, SLOT(reject()));

    if (dialog.exec() != QDialog::Accepted) {
        return;
    }

    m_cameraDevice = deviceEdit->text().trimmed();
    m_inferProgram = AIInferenceThread::resolveProgramPath(programEdit->text().trimmed());
    m_captureDir = captureDirEdit->text().trimmed();
    m_aiThread->setProgramPath(m_inferProgram);
    saveSettings();
}

void MainWindow::openHistoryDialog()
{
    QDialog dialog(this);
    dialog.setWindowTitle(QStringLiteral("历史记录"));
    dialog.setMinimumSize(640, 420);

    QListWidget *listWidget = new QListWidget(&dialog);
    listWidget->addItems(m_historyRecords);

    QDialogButtonBox *buttonBox = new QDialogButtonBox(QDialogButtonBox::Close, &dialog);
    QVBoxLayout *layout = new QVBoxLayout(&dialog);
    layout->addWidget(new QLabel(QStringLiteral("最近识别记录（最多保留 100 条）"), &dialog));
    layout->addWidget(listWidget);
    layout->addWidget(buttonBox);

    connect(buttonBox, SIGNAL(accepted()), &dialog, SLOT(accept()));
    connect(buttonBox, SIGNAL(rejected()), &dialog, SLOT(reject()));
    buttonBox->button(QDialogButtonBox::Close)->setText(QStringLiteral("关闭"));

    dialog.exec();
}
