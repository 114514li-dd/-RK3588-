/**
 * @file mainwidget.cpp
 * @brief OneNET 物模型监控主界面实现
 */

#include "mainwidget.h"
#include "main.h"

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QCheckBox>
#include <QFrame>
#include <QGroupBox>
#include <QIntValidator>
#include <QFile>
#include <QTextStream>
#include <QDir>
#include <QCoreApplication>
#include <QStandardPaths>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QUrlQuery>
#include <QDateTime>
#include <QMessageBox>
#include <QValueAxis>
#include <QStyle>
#include <QPainter>
#include <QGraphicsDropShadowEffect>
#include <QDebug>
#include <QSslSocket>
#include <QSslError>
#include <QProcess>
#include <QFile>
#include <QResizeEvent>
#include <QShowEvent>
#include <QtGlobal>

#if QT_VERSION >= QT_VERSION_CHECK(6, 0, 0)
#include <QStringConverter>
#endif

// ============================================================
// OneNET 平台连接参数（已按你的账号配置）
// ============================================================
static const char *ONENET_API_HOST        = "https://iot-api.heclouds.com";
static const char *ONENET_PRODUCT_ID      = "006jQmKSbY";   // 产品 ID
static const char *ONENET_DEVICE_NAME     = "Test";         // 设备名称
// 安全鉴权 Token（与 MQTT 连接 token 相同，Header: Authorization）
static const char *ONENET_AUTH_TOKEN        =
    "version=2018-10-31&res=products%2F006jQmKSbY%2Fdevices%2FTest"
    "&et=1789656062&method=md5&sign=rMHi26dJmaqDurnom7AQEQ%3D%3D";
// 设备密钥（仅用于 Token 过期后重新生成，程序运行不需要填写）
// cmVPVVRvMTc4YUpDa04yQTEzRHFESTVwMkVmRUxkOWI=
// ============================================================

static const char *PROP_TEMP  = "Temp";
static const char *PROP_HUM   = "Hum";
static const char *PROP_LED   = "Led";
static const char *PROP_ALARM = "Alarm";

static const int kPollIntervalMs  = 1000;
static const int kBlinkIntervalMs = 500;
static const int kMaxChartPoints  = 35;
static const char *kCfgFileName   = "threshold.cfg";

/** @brief 判断 OneNET 物模型 API 是否成功（兼容 code=0 与 success=true） */
static bool isOneNetApiSuccess(const QJsonObject &root)
{
    if (root.value(QStringLiteral("success")).toBool(false)) {
        return true;
    }
    if (root.value(QStringLiteral("code")).toInt(-1) == 0) {
        return true;
    }
    return root.value(QStringLiteral("msg")).toString().compare(
               QLatin1String("succ"), Qt::CaseInsensitive) == 0;
}

/** @brief 从查询响应中提取属性列表（兼容 Studio 与 thingmodel 两种格式） */
static QJsonArray extractPropertyList(const QJsonObject &root)
{
    const QJsonValue dataVal = root.value(QStringLiteral("data"));
    if (dataVal.isArray()) {
        return dataVal.toArray();
    }
    if (dataVal.isObject()) {
        const QJsonObject dataObj = dataVal.toObject();
        const QJsonArray list = dataObj.value(QStringLiteral("list")).toArray();
        if (!list.isEmpty()) {
            return list;
        }
        return dataObj.value(QStringLiteral("properties")).toArray();
    }
    return QJsonArray();
}

MainWidget::MainWidget(QWidget *parent)
    : QWidget(parent)
    , m_networkManager(new QNetworkAccessManager(this))
    , m_pollTimer(new QTimer(this))
    , m_blinkTimer(new QTimer(this))
    , m_blinkRedPhase(true)
    , m_useCurlBackend(false)
    , m_curlQueryBusy(false)
    , m_temperature(-1)
    , m_humidity(-1)
    , m_ledOn(false)
    , m_alarmOn(false)
    , m_hasTemp(false)
    , m_hasHum(false)
    , m_hasLed(false)
    , m_hasAlarm(false)
    , m_thresholdA(30)
    , m_thresholdB(70)
    , m_autoAlarmEnabled(true)
    , m_pendingAlarmSet(false)
    , m_tempSeries(new QLineSeries())
    , m_humSeries(new QLineSeries())
    , m_chart(new QChart())
    , m_chartView(nullptr)
    , m_axisX(nullptr)
    , m_chartIndex(0)
    , m_uiScale(1.0)
    , m_titleLabel(nullptr)
    , m_alarmBarLabel(nullptr)
    , m_tempMainLabel(nullptr)
    , m_tempCompareLabel(nullptr)
    , m_humMainLabel(nullptr)
    , m_humCompareLabel(nullptr)
    , m_ledDotLabel(nullptr)
    , m_ledTextLabel(nullptr)
    , m_alarmDotLabel(nullptr)
    , m_alarmTextLabel(nullptr)
    , m_netHintLabel(nullptr)
    , m_thresholdAEdit(nullptr)
    , m_thresholdBEdit(nullptr)
    , m_autoAlarmCheck(nullptr)
    , m_saveThresholdBtn(nullptr)
    , m_ledOnBtn(nullptr)
    , m_ledOffBtn(nullptr)
    , m_alarmOnBtn(nullptr)
    , m_alarmOffBtn(nullptr)
    , m_closeBtn(nullptr)
{
    setWindowFlags(Qt::Window | Qt::FramelessWindowHint);
    setWindowTitle(QStringLiteral(APP_NAME));

    setupUi();
    applyGlobalStyle();
    applyUiScale();

    connectSignals();
    loadThresholdsFromCfg();
    initNetworkBackend();

    m_pollTimer->setInterval(kPollIntervalMs);
    m_pollTimer->start();
    onPollTimerTimeout();

    m_blinkTimer->setInterval(kBlinkIntervalMs);
}

MainWidget::~MainWidget() = default;

void MainWidget::resizeEvent(QResizeEvent *event)
{
    QWidget::resizeEvent(event);
    applyUiScale();
}

void MainWidget::showEvent(QShowEvent *event)
{
    QWidget::showEvent(event);
    applyUiScale();
}

void MainWidget::applyUiScale()
{
    if (width() <= 0 || height() <= 0) {
        return;
    }

    const qreal sx = width() / qreal(APP_WIDTH);
    const qreal sy = height() / qreal(APP_HEIGHT);
    m_uiScale = qBound(0.75, qMin(sx, sy), 2.5);

    const auto px = [this](int base) { return qMax(1, qRound(base * m_uiScale)); };

    setStyleSheet(QStringLiteral(
        "MainWidget {"
        "  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
        "    stop:0 #DCEEF9, stop:0.5 #EBF5FB, stop:1 #F8FCFF);"
        "  font-family: '" APP_FONT_FALLBACK "';"
        "  color: #1A3A5C;"
        "}"
        "QLabel#titleLabel {"
        "  font-size: %1px; font-weight: bold; color: #0D47A1; padding: %2px;"
        "}"
        "QFrame#cardFrame {"
        "  background: #FFFFFF; border-radius: %3px; border: 1px solid #D6EAF8;"
        "}"
        "QLabel#cardTitle {"
        "  font-size: %4px; font-weight: bold; color: #1565C0;"
        "}"
        "QLabel#dataMainLabel {"
        "  font-size: %5px; font-weight: bold; color: #1976D2;"
        "}"
        "QLabel#dataSubLabel {"
        "  font-size: %6px; color: #607D8B;"
        "}"
        "QLabel#alarmBarNormal, QLabel#alarmBarWarnRed, QLabel#alarmBarWarnGreen {"
        "  font-size: %4px; font-weight: bold; border-radius: %7px; padding: %8px;"
        "}"
        "QLabel#alarmBarNormal { background: #C8E6C9; color: #1B5E20; }"
        "QLabel#alarmBarWarnRed { background: #FFCDD2; color: #B71C1C; }"
        "QLabel#alarmBarWarnGreen { background: #A5D6A7; color: #1B5E20; }"
        "QLabel#dotOnGreen {"
        "  background: #43A047; border-radius: %9px; border: 2px solid #2E7D32;"
        "}"
        "QLabel#dotOff {"
        "  background: #B0BEC5; border-radius: %9px; border: 2px solid #90A4AE;"
        "}"
        "QLabel#dotOnRed {"
        "  background: #E53935; border-radius: %9px; border: 2px solid #C62828;"
        "}"
        "QLabel#statusText { font-size: %4px; font-weight: bold; }"
        "QLabel#hintLabel { font-size: %10px; color: #78909C; }"
        "QLineEdit {"
        "  border: 1px solid #CFD8DC; border-radius: %7px;"
        "  padding: %11px %12px; background: #FAFAFA;"
        "}"
        "QLineEdit:focus { border: 1px solid #42A5F5; background: #FFFFFF; }"
        "QCheckBox#autoAlarmCheck { font-weight: bold; color: #37474F; }"
        "QPushButton {"
        "  border: none; border-radius: %7px; padding: %11px %12px;"
        "  font-weight: bold; color: white; background: #64B5F6;"
        "}"
        "QPushButton:hover { background: #42A5F5; }"
        "QPushButton:pressed { background: #1E88E5; }"
        "QPushButton#primaryBtn { background: #1976D2; }"
        "QPushButton#primaryBtn:hover { background: #1565C0; }"
        "QPushButton#successBtn { background: #43A047; }"
        "QPushButton#successBtn:hover { background: #2E7D32; }"
        "QPushButton#dangerBtn { background: #E53935; }"
        "QPushButton#dangerBtn:hover { background: #C62828; }"
        "QPushButton#grayBtn { background: #78909C; }"
        "QPushButton#grayBtn:hover { background: #607D8B; }"
        "QPushButton#closeBtn {"
        "  background: transparent; color: #546E7A; border: none;"
        "  font-size: %13px; font-weight: bold; padding: 0;"
        "  min-width: %14px; max-width: %14px; min-height: %14px; max-height: %14px;"
        "  border-radius: %7px;"
        "}"
        "QPushButton#closeBtn:hover { background: #FFCDD2; color: #B71C1C; }"
        "QPushButton#closeBtn:pressed { background: #EF9A9A; color: #880E4F; }"
    ).arg(px(20)).arg(px(4)).arg(px(14)).arg(px(14)).arg(px(32)).arg(px(12))
     .arg(px(10)).arg(px(10)).arg(px(14)).arg(px(11)).arg(px(6)).arg(px(16))
     .arg(px(22)).arg(px(36)));

    if (m_alarmBarLabel) {
        m_alarmBarLabel->setMinimumHeight(px(44));
    }
    if (m_ledDotLabel) {
        m_ledDotLabel->setFixedSize(px(28), px(28));
    }
    if (m_alarmDotLabel) {
        m_alarmDotLabel->setFixedSize(px(28), px(28));
    }
    if (m_chartView) {
        m_chartView->setMinimumHeight(px(280));
    }
    if (m_closeBtn) {
        m_closeBtn->setFixedSize(px(36), px(36));
    }
    if (QLayout *root = layout()) {
        root->setContentsMargins(px(20), px(16), px(20), px(16));
        root->setSpacing(px(12));
    }
}

// ============================================================
// UI 构建：顶部标题+报警栏 | 左侧数据/阈值/图表 | 右侧手动控制
// ============================================================

void MainWidget::setupUi()
{
    QVBoxLayout *root = new QVBoxLayout(this);
    root->setContentsMargins(20, 16, 20, 16);
    root->setSpacing(12);

    // ---------- 顶部标题 + 关闭按钮 ----------
    m_titleLabel = new QLabel(QStringLiteral("Al赋能设计，设计点亮Al"));
    m_titleLabel->setObjectName(QStringLiteral("titleLabel"));
    m_titleLabel->setAlignment(Qt::AlignCenter);

    m_closeBtn = new QPushButton(QStringLiteral("×"));
    m_closeBtn->setObjectName(QStringLiteral("closeBtn"));
    m_closeBtn->setFlat(true);
    m_closeBtn->setCursor(Qt::PointingHandCursor);
    m_closeBtn->setToolTip(QStringLiteral("关闭"));
    m_closeBtn->setFixedSize(36, 36);

    QHBoxLayout *titleRow = new QHBoxLayout();
    titleRow->setSpacing(0);
    titleRow->addStretch(1);
    titleRow->addWidget(m_titleLabel, 0, Qt::AlignCenter);
    titleRow->addStretch(1);
    titleRow->addWidget(m_closeBtn, 0, Qt::AlignRight | Qt::AlignVCenter);
    root->addLayout(titleRow);

    // ---------- 顶部报警提示栏 ----------
    m_alarmBarLabel = new QLabel(QStringLiteral("● 系统正常 · 温湿度均在设定阈值内"));
    m_alarmBarLabel->setObjectName(QStringLiteral("alarmBarNormal"));
    m_alarmBarLabel->setAlignment(Qt::AlignCenter);
    m_alarmBarLabel->setMinimumHeight(44);
    root->addWidget(m_alarmBarLabel);

    QHBoxLayout *bodyRow = new QHBoxLayout();
    bodyRow->setSpacing(16);

    // ==================== 左侧面板 ====================
    QVBoxLayout *leftPanel = new QVBoxLayout();
    leftPanel->setSpacing(12);

    // 温湿度实时数值卡片
    QFrame *dataCard = new QFrame();
    dataCard->setObjectName(QStringLiteral("cardFrame"));
    applyCardShadow(dataCard);
    QGridLayout *dataGrid = new QGridLayout(dataCard);
    dataGrid->setSpacing(10);

    QLabel *tempTitle = new QLabel(QStringLiteral("温度 Temp"));
    tempTitle->setObjectName(QStringLiteral("cardTitle"));
    m_tempMainLabel = new QLabel(QStringLiteral("-- ℃"));
    m_tempMainLabel->setObjectName(QStringLiteral("dataMainLabel"));
    m_tempCompareLabel = new QLabel(QStringLiteral("阈值 A：-- ℃"));
    m_tempCompareLabel->setObjectName(QStringLiteral("dataSubLabel"));

    QLabel *humTitle = new QLabel(QStringLiteral("湿度 Hum"));
    humTitle->setObjectName(QStringLiteral("cardTitle"));
    m_humMainLabel = new QLabel(QStringLiteral("-- %RH"));
    m_humMainLabel->setObjectName(QStringLiteral("dataMainLabel"));
    m_humCompareLabel = new QLabel(QStringLiteral("阈值 B：-- %RH"));
    m_humCompareLabel->setObjectName(QStringLiteral("dataSubLabel"));

    dataGrid->addWidget(tempTitle, 0, 0);
    dataGrid->addWidget(m_tempMainLabel, 1, 0);
    dataGrid->addWidget(m_tempCompareLabel, 2, 0);
    dataGrid->addWidget(humTitle, 0, 1);
    dataGrid->addWidget(m_humMainLabel, 1, 1);
    dataGrid->addWidget(m_humCompareLabel, 2, 1);
    leftPanel->addWidget(dataCard);

    // 阈值设置卡片
    QFrame *thresholdCard = new QFrame();
    thresholdCard->setObjectName(QStringLiteral("cardFrame"));
    applyCardShadow(thresholdCard);
    QVBoxLayout *thresholdLay = new QVBoxLayout(thresholdCard);

    QLabel *thresholdTitle = new QLabel(QStringLiteral("阈值自定义报警"));
    thresholdTitle->setObjectName(QStringLiteral("cardTitle"));
    thresholdLay->addWidget(thresholdTitle);

    QGridLayout *thresholdGrid = new QGridLayout();
    thresholdGrid->addWidget(new QLabel(QStringLiteral("温度阈值 A(0~100)：")), 0, 0);
    m_thresholdAEdit = new QLineEdit(QString::number(m_thresholdA));
    m_thresholdAEdit->setValidator(new QIntValidator(0, 100, this));
    thresholdGrid->addWidget(m_thresholdAEdit, 0, 1);

    thresholdGrid->addWidget(new QLabel(QStringLiteral("湿度阈值 B(0~100)：")), 1, 0);
    m_thresholdBEdit = new QLineEdit(QString::number(m_thresholdB));
    m_thresholdBEdit->setValidator(new QIntValidator(0, 100, this));
    thresholdGrid->addWidget(m_thresholdBEdit, 1, 1);
    thresholdLay->addLayout(thresholdGrid);

    m_autoAlarmCheck = new QCheckBox(QStringLiteral("启用自动阈值报警"));
    m_autoAlarmCheck->setChecked(m_autoAlarmEnabled);
    m_autoAlarmCheck->setObjectName(QStringLiteral("autoAlarmCheck"));
    thresholdLay->addWidget(m_autoAlarmCheck);

    m_saveThresholdBtn = new QPushButton(QStringLiteral("保存阈值到本地 cfg"));
    m_saveThresholdBtn->setObjectName(QStringLiteral("primaryBtn"));
    thresholdLay->addWidget(m_saveThresholdBtn);
    leftPanel->addWidget(thresholdCard);

    // 双折线图卡片
    QFrame *chartCard = new QFrame();
    chartCard->setObjectName(QStringLiteral("cardFrame"));
    applyCardShadow(chartCard);
    QVBoxLayout *chartLay = new QVBoxLayout(chartCard);

    QLabel *chartTitle = new QLabel(QStringLiteral("温湿度实时曲线（最近 35 组）"));
    chartTitle->setObjectName(QStringLiteral("cardTitle"));
    chartLay->addWidget(chartTitle);

    m_tempSeries->setName(QStringLiteral("温度"));
    m_humSeries->setName(QStringLiteral("湿度"));
    m_chart->addSeries(m_tempSeries);
    m_chart->addSeries(m_humSeries);
    m_chart->legend()->setVisible(true);
    m_chart->setAnimationOptions(QChart::NoAnimation);
    m_chart->setBackgroundVisible(false);

    m_axisX = new QValueAxis();
    m_axisX->setTitleText(QStringLiteral("采样序号"));
    m_axisX->setLabelFormat("%d");
    m_axisX->setRange(0, kMaxChartPoints);

    QValueAxis *axisY = new QValueAxis();
    axisY->setTitleText(QStringLiteral("数值"));
    axisY->setLabelFormat("%d");
    axisY->setRange(0, 100);

    m_chart->addAxis(m_axisX, Qt::AlignBottom);
    m_chart->addAxis(axisY, Qt::AlignLeft);
    m_tempSeries->attachAxis(m_axisX);
    m_tempSeries->attachAxis(axisY);
    m_humSeries->attachAxis(m_axisX);
    m_humSeries->attachAxis(axisY);

    m_chartView = new QChartView(m_chart);
    m_chartView->setRenderHint(QPainter::Antialiasing);
    m_chartView->setMinimumHeight(280);
    chartLay->addWidget(m_chartView, 1);
    leftPanel->addWidget(chartCard, 1);

    bodyRow->addLayout(leftPanel, 3);

    // ==================== 右侧手动控制面板 ====================
    QFrame *rightCard = new QFrame();
    rightCard->setObjectName(QStringLiteral("cardFrame"));
    applyCardShadow(rightCard);
    QVBoxLayout *rightLay = new QVBoxLayout(rightCard);
    rightLay->setSpacing(16);

    QLabel *rightTitle = new QLabel(QStringLiteral("设备状态 & 手动控制"));
    rightTitle->setObjectName(QStringLiteral("cardTitle"));
    rightLay->addWidget(rightTitle);

    // LED 圆形指示灯
    QHBoxLayout *ledRow = new QHBoxLayout();
    m_ledDotLabel = new QLabel();
    m_ledDotLabel->setFixedSize(28, 28);
    m_ledDotLabel->setObjectName(QStringLiteral("dotOff"));
    m_ledTextLabel = new QLabel(QStringLiteral("LED：未知"));
    m_ledTextLabel->setObjectName(QStringLiteral("statusText"));
    ledRow->addWidget(m_ledDotLabel);
    ledRow->addWidget(m_ledTextLabel, 1);
    rightLay->addLayout(ledRow);

    QHBoxLayout *ledBtnRow = new QHBoxLayout();
    m_ledOnBtn = new QPushButton(QStringLiteral("LED 开启"));
    m_ledOffBtn = new QPushButton(QStringLiteral("LED 关闭"));
    m_ledOnBtn->setObjectName(QStringLiteral("successBtn"));
    m_ledOffBtn->setObjectName(QStringLiteral("grayBtn"));
    ledBtnRow->addWidget(m_ledOnBtn);
    ledBtnRow->addWidget(m_ledOffBtn);
    rightLay->addLayout(ledBtnRow);

    rightLay->addSpacing(8);

    // 蜂鸣器圆形指示灯
    QHBoxLayout *alarmRow = new QHBoxLayout();
    m_alarmDotLabel = new QLabel();
    m_alarmDotLabel->setFixedSize(28, 28);
    m_alarmDotLabel->setObjectName(QStringLiteral("dotOff"));
    m_alarmTextLabel = new QLabel(QStringLiteral("蜂鸣器：未知"));
    m_alarmTextLabel->setObjectName(QStringLiteral("statusText"));
    alarmRow->addWidget(m_alarmDotLabel);
    alarmRow->addWidget(m_alarmTextLabel, 1);
    rightLay->addLayout(alarmRow);

    QHBoxLayout *alarmBtnRow = new QHBoxLayout();
    m_alarmOnBtn = new QPushButton(QStringLiteral("蜂鸣器 开启"));
    m_alarmOffBtn = new QPushButton(QStringLiteral("蜂鸣器 关闭"));
    m_alarmOnBtn->setObjectName(QStringLiteral("dangerBtn"));
    m_alarmOffBtn->setObjectName(QStringLiteral("grayBtn"));
    alarmBtnRow->addWidget(m_alarmOnBtn);
    alarmBtnRow->addWidget(m_alarmOffBtn);
    rightLay->addLayout(alarmBtnRow);

    m_netHintLabel = new QLabel(QStringLiteral("网络：初始化..."));
    m_netHintLabel->setObjectName(QStringLiteral("hintLabel"));
    m_netHintLabel->setWordWrap(true);
    rightLay->addWidget(m_netHintLabel);

    rightLay->addStretch();
    bodyRow->addWidget(rightCard, 1);
    root->addLayout(bodyRow, 1);
}

void MainWidget::applyCardShadow(QWidget *card)
{
    QGraphicsDropShadowEffect *shadow = new QGraphicsDropShadowEffect(card);
    shadow->setBlurRadius(18);
    shadow->setOffset(0, 4);
    shadow->setColor(QColor(30, 80, 140, 45));
    card->setGraphicsEffect(shadow);
}

void MainWidget::applyGlobalStyle()
{
    // 折线颜色：温度红、湿度蓝
    QPen tempPen(QColor(QStringLiteral("#E53935")));
    tempPen.setWidth(2);
    m_tempSeries->setPen(tempPen);

    QPen humPen(QColor(QStringLiteral("#1E88E5")));
    humPen.setWidth(2);
    m_humSeries->setPen(humPen);
}

void MainWidget::connectSignals()
{
    connect(m_pollTimer, &QTimer::timeout, this, &MainWidget::onPollTimerTimeout);
    connect(m_blinkTimer, &QTimer::timeout, this, &MainWidget::onBlinkTimerTimeout);
    connect(m_saveThresholdBtn, &QPushButton::clicked, this, &MainWidget::onSaveThresholdClicked);
    connect(m_autoAlarmCheck, &QCheckBox::toggled, this, &MainWidget::onAutoAlarmToggled);
    connect(m_ledOnBtn, &QPushButton::clicked, this, &MainWidget::onLedOnClicked);
    connect(m_ledOffBtn, &QPushButton::clicked, this, &MainWidget::onLedOffClicked);
    connect(m_alarmOnBtn, &QPushButton::clicked, this, &MainWidget::onAlarmOnClicked);
    connect(m_alarmOffBtn, &QPushButton::clicked, this, &MainWidget::onAlarmOffClicked);
    connect(m_closeBtn, &QPushButton::clicked, this, &MainWidget::onCloseClicked);
}

// ============================================================
// 本地 cfg 文件持久化（threshold.cfg）
// ============================================================

QString MainWidget::cfgFilePath() const
{
#if defined(Q_OS_LINUX)
    const QString dir = QStandardPaths::writableLocation(QStandardPaths::AppConfigLocation);
    if (!dir.isEmpty()) {
        QDir().mkpath(dir);
        return dir + QDir::separator() + QLatin1String(kCfgFileName);
    }
#endif
    return QCoreApplication::applicationDirPath() + QDir::separator() + QLatin1String(kCfgFileName);
}

void MainWidget::loadThresholdsFromCfg()
{
    QFile file(cfgFilePath());
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        qDebug() << "[CFG] 未找到 cfg，使用默认阈值 A=30 B=70";
        m_thresholdAEdit->setText(QString::number(m_thresholdA));
        m_thresholdBEdit->setText(QString::number(m_thresholdB));
        return;
    }

    QTextStream in(&file);
#if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)
    in.setCodec("UTF-8");
#else
    in.setEncoding(QStringConverter::Utf8);
#endif
    while (!in.atEnd()) {
        const QString line = in.readLine().trimmed();
        if (line.startsWith(QLatin1Char('#')) || !line.contains(QLatin1Char('='))) {
            continue;
        }
        const QStringList kv = line.split(QLatin1Char('='));
        if (kv.size() != 2) {
            continue;
        }
        const QString key = kv.at(0).trimmed();
        const QString val = kv.at(1).trimmed();
        if (key == QLatin1String("ThresholdA")) {
            m_thresholdA = qBound(0, val.toInt(), 100);
        } else if (key == QLatin1String("ThresholdB")) {
            m_thresholdB = qBound(0, val.toInt(), 100);
        } else if (key == QLatin1String("AutoAlarmEnabled")) {
            m_autoAlarmEnabled = (val == QLatin1String("1") || val.compare(QLatin1String("true"), Qt::CaseInsensitive) == 0);
        }
    }
    file.close();

    m_thresholdAEdit->setText(QString::number(m_thresholdA));
    m_thresholdBEdit->setText(QString::number(m_thresholdB));
    m_autoAlarmCheck->setChecked(m_autoAlarmEnabled);
    qDebug() << "[CFG] 已加载 ThresholdA=" << m_thresholdA << "ThresholdB=" << m_thresholdB
             << "AutoAlarm=" << m_autoAlarmEnabled;
}

void MainWidget::saveThresholdsToCfg()
{
    QFile file(cfgFilePath());
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text | QIODevice::Truncate)) {
        qDebug() << "[CFG] 写入失败:" << file.errorString();
        return;
    }
    QTextStream out(&file);
#if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)
    out.setCodec("UTF-8");
#else
    out.setEncoding(QStringConverter::Utf8);
#endif
    out << "# OneNET Monitor threshold config\n";
    out << "ThresholdA=" << m_thresholdA << "\n";
    out << "ThresholdB=" << m_thresholdB << "\n";
    out << "AutoAlarmEnabled=" << (m_autoAlarmEnabled ? 1 : 0) << "\n";
    file.close();
    qDebug() << "[CFG] 已保存到" << cfgFilePath();
}

bool MainWidget::validateThresholdInput(QLineEdit *edit, int *outValue) const
{
    if (!edit || !outValue) {
        return false;
    }
    bool ok = false;
    const int v = edit->text().trimmed().toInt(&ok);
    if (!ok || v < 0 || v > 100) {
        return false;
    }
    *outValue = v;
    return true;
}

void MainWidget::onSaveThresholdClicked()
{
    int a = 0, b = 0;
    if (!validateThresholdInput(m_thresholdAEdit, &a)) {
        QMessageBox::warning(this, QStringLiteral("输入错误"),
                             QStringLiteral("温度阈值 A 仅允许 0~100 的整数。"));
        return;
    }
    if (!validateThresholdInput(m_thresholdBEdit, &b)) {
        QMessageBox::warning(this, QStringLiteral("输入错误"),
                             QStringLiteral("湿度阈值 B 仅允许 0~100 的整数。"));
        return;
    }
    m_thresholdA = a;
    m_thresholdB = b;
    m_autoAlarmEnabled = m_autoAlarmCheck->isChecked();
    saveThresholdsToCfg();
    refreshDataLabels();
    evaluateAutoAlarm();
    refreshAlarmBar();
    QMessageBox::information(this, QStringLiteral("保存成功"),
                             QStringLiteral("阈值已写入 threshold.cfg，重启后仍有效。"));
}

void MainWidget::onAutoAlarmToggled(bool checked)
{
    m_autoAlarmEnabled = checked;
    saveThresholdsToCfg();
    if (checked) {
        evaluateAutoAlarm();
    }
}

// ============================================================
// 网络请求封装
// ============================================================

QString MainWidget::apiBaseUrl() const
{
    return QString::fromUtf8(ONENET_API_HOST);
}

void MainWidget::applyApiHeaders(QNetworkRequest &request, bool isPost) const
{
    if (isPost) {
        request.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    }
    request.setRawHeader("Authorization", QByteArray(ONENET_AUTH_TOKEN));
}

void MainWidget::prepareNetworkReply(QNetworkReply *reply) const
{
    if (!reply) {
        return;
    }
    // 忽略 SSL 证书校验异常（内网/旧版 Qt 常见）；前提是 OpenSSL DLL 已就位
    connect(reply, &QNetworkReply::sslErrors, reply, [reply](const QList<QSslError> &) {
        reply->ignoreSslErrors();
    });
}

void MainWidget::ensureOpenSslDlls(const QString &appDir)
{
#if defined(Q_OS_WIN)
    static const char *kDllNames[] = { "libeay32.dll", "ssleay32.dll" };
    static const char *kSourceDirs[] = {
        "C:/Qt/Qt5.8.0/Tools/QtCreator/bin",
        "C:/Qt/Qt5.8.0/Tools/mingw530_32/opt/bin",
        nullptr
    };

    for (const char *name : kDllNames) {
        const QString dest = appDir + QChar(QLatin1Char('/')) + QLatin1String(name);
        if (QFile::exists(dest)) {
            continue;
        }
        for (int i = 0; kSourceDirs[i] != nullptr; ++i) {
            const QString src = QString::fromLatin1(kSourceDirs[i]) + QChar(QLatin1Char('/')) + QLatin1String(name);
            if (QFile::exists(src) && QFile::copy(src, dest)) {
                qDebug() << "[NET] 已复制" << name << "到" << appDir;
                break;
            }
        }
    }
#else
    Q_UNUSED(appDir);
#endif
}

QString MainWidget::findCurlExecutable()
{
    QStringList candidates;
#if defined(Q_OS_WIN)
    candidates << QStringLiteral("C:/Windows/System32/curl.exe")
               << QStringLiteral("C:/Windows/SysWOW64/curl.exe")
               << QStringLiteral("curl.exe");
#else
    candidates << QStringLiteral("/usr/bin/curl")
               << QStringLiteral("/bin/curl")
               << QStringLiteral("curl");
#endif
    for (const QString &path : candidates) {
        QProcess probe;
        probe.start(path, QStringList() << QStringLiteral("--version"));
        if (probe.waitForStarted(1500) && probe.waitForFinished(3000) && probe.exitCode() == 0) {
            return path;
        }
    }
    return QString();
}

void MainWidget::initNetworkBackend()
{
    const QString appDir = QCoreApplication::applicationDirPath();
    ensureOpenSslDlls(appDir);

    if (QSslSocket::supportsSsl()) {
        m_useCurlBackend = false;
        qDebug() << "[NET] Qt SSL 可用:" << QSslSocket::sslLibraryVersionString();
        m_netHintLabel->setText(QStringLiteral("网络：Qt HTTPS 就绪，正在连接..."));
        return;
    }

    qDebug() << "[NET] Qt SSL 不可用，尝试 curl 备用通道";
    m_curlPath = findCurlExecutable();
    if (!m_curlPath.isEmpty()) {
        m_useCurlBackend = true;
        m_netHintLabel->setText(QStringLiteral("已切换 curl 通道连接 OneNET"));
        qDebug() << "[NET] 使用 curl:" << m_curlPath;
        return;
    }

    m_useCurlBackend = false;
#if defined(Q_OS_WIN)
    m_netHintLabel->setText(QStringLiteral(
        "无法联网：Qt 无 SSL 且未找到 curl.exe\n"
        "请安装 Windows 10+ 或把 libeay32.dll/ssleay32.dll 放到 exe 同目录"));
#else
    m_netHintLabel->setText(QStringLiteral(
        "无法联网：Qt 无 SSL 且未找到 curl\n"
        "请在板卡上安装 openssl 与 curl，或确保 Qt 编译时启用了 SSL"));
#endif
}

void MainWidget::logNetworkError(const QString &action, const QString &detail) const
{
    // 简易错误逻辑：控制台输出，界面仅显示最后一行提示，不弹窗
    qDebug() << "[NET]" << action << "失败:" << detail << "-> 下次轮询静默重试";
}

void MainWidget::queryDeviceProperty()
{
    if (m_useCurlBackend) {
        queryDevicePropertyViaCurl();
        return;
    }

    // 物模型属性查询（Qt HTTPS）
    QUrl url(apiBaseUrl() + QStringLiteral("/thingmodel/query-device-property"));
    QUrlQuery query;
    query.addQueryItem(QStringLiteral("product_id"), QString::fromUtf8(ONENET_PRODUCT_ID));
    query.addQueryItem(QStringLiteral("device_name"), QString::fromUtf8(ONENET_DEVICE_NAME));
    url.setQuery(query);

    QNetworkRequest request(url);
    applyApiHeaders(request, false);

    QNetworkReply *reply = m_networkManager->get(request);
    prepareNetworkReply(reply);
    connect(reply, &QNetworkReply::finished, this, &MainWidget::onQueryFinished);
}

void MainWidget::setDeviceProperty(const QString &identifier, const QVariant &value)
{
    if (m_useCurlBackend) {
        setDevicePropertyViaCurl(identifier, value);
        return;
    }

    QUrl url(apiBaseUrl() + QStringLiteral("/thingmodel/set-device-property"));

    QJsonObject params;
    params.insert(identifier, QJsonValue::fromVariant(value));

    QJsonObject body;
    body.insert(QStringLiteral("product_id"), QString::fromUtf8(ONENET_PRODUCT_ID));
    body.insert(QStringLiteral("device_name"), QString::fromUtf8(ONENET_DEVICE_NAME));
    body.insert(QStringLiteral("params"), params);

    QNetworkRequest request(url);
    applyApiHeaders(request, true);

    QNetworkReply *reply = m_networkManager->post(request,
        QJsonDocument(body).toJson(QJsonDocument::Compact));
    reply->setProperty("setIdentifier", identifier);
    prepareNetworkReply(reply);
    connect(reply, &QNetworkReply::finished, this, &MainWidget::onSetFinished);
}

void MainWidget::onPollTimerTimeout()
{
    queryDeviceProperty();
}

void MainWidget::queryDevicePropertyViaCurl()
{
    if (m_curlPath.isEmpty() || m_curlQueryBusy) {
        return;
    }
    m_curlQueryBusy = true;

    const QString url = apiBaseUrl()
        + QStringLiteral("/thingmodel/query-device-property?product_id=")
        + QString::fromUtf8(ONENET_PRODUCT_ID)
        + QStringLiteral("&device_name=")
        + QString::fromUtf8(ONENET_DEVICE_NAME);

    QProcess *proc = new QProcess(this);
    proc->setProperty("netAction", QStringLiteral("query"));
    connect(proc, static_cast<void(QProcess::*)(int, QProcess::ExitStatus)>(&QProcess::finished),
            this, &MainWidget::onCurlQueryFinished);

    const QStringList args = {
        QStringLiteral("-s"),
        QStringLiteral("--max-time"), QStringLiteral("8"),
        url,
        QStringLiteral("-H"),
        QStringLiteral("Authorization: ") + QString::fromUtf8(ONENET_AUTH_TOKEN)
    };
    proc->start(m_curlPath, args);
}

void MainWidget::setDevicePropertyViaCurl(const QString &identifier, const QVariant &value)
{
    if (m_curlPath.isEmpty()) {
        return;
    }

    QJsonObject params;
    params.insert(identifier, QJsonValue::fromVariant(value));
    QJsonObject body;
    body.insert(QStringLiteral("product_id"), QString::fromUtf8(ONENET_PRODUCT_ID));
    body.insert(QStringLiteral("device_name"), QString::fromUtf8(ONENET_DEVICE_NAME));
    body.insert(QStringLiteral("params"), params);
    const QByteArray payload = QJsonDocument(body).toJson(QJsonDocument::Compact);

    QProcess *proc = new QProcess(this);
    proc->setProperty("netAction", QStringLiteral("set"));
    proc->setProperty("setIdentifier", identifier);
    connect(proc, static_cast<void(QProcess::*)(int, QProcess::ExitStatus)>(&QProcess::finished),
            this, &MainWidget::onCurlSetFinished);

    const QString url = apiBaseUrl() + QStringLiteral("/thingmodel/set-device-property");
    const QStringList args = {
        QStringLiteral("-s"),
        QStringLiteral("--max-time"), QStringLiteral("8"),
        QStringLiteral("-X"), QStringLiteral("POST"),
        url,
        QStringLiteral("-H"),
        QStringLiteral("Authorization: ") + QString::fromUtf8(ONENET_AUTH_TOKEN),
        QStringLiteral("-H"), QStringLiteral("Content-Type: application/json"),
        QStringLiteral("-d"), QString::fromUtf8(payload)
    };
    proc->start(m_curlPath, args);
}

void MainWidget::onCurlQueryFinished(int exitCode, QProcess::ExitStatus status)
{
    QProcess *proc = qobject_cast<QProcess *>(sender());
    if (!proc) {
        return;
    }
    m_curlQueryBusy = false;

    const QByteArray out = proc->readAllStandardOutput();
    const QByteArray err = proc->readAllStandardError();
    proc->deleteLater();

    if (status != QProcess::NormalExit || exitCode != 0) {
        logNetworkError(QStringLiteral("curl query"),
                        QString::fromUtf8(err.isEmpty() ? out : err));
        m_netHintLabel->setText(QStringLiteral("curl 查询失败(code=%1)，1秒后重试").arg(exitCode));
        return;
    }

    handleQueryResponse(out);
}

void MainWidget::onCurlSetFinished(int exitCode, QProcess::ExitStatus status)
{
    QProcess *proc = qobject_cast<QProcess *>(sender());
    if (!proc) {
        return;
    }

    const QString id = proc->property("setIdentifier").toString();
    const QByteArray out = proc->readAllStandardOutput();
    const QByteArray err = proc->readAllStandardError();
    proc->deleteLater();

    if (id == QLatin1String(PROP_ALARM)) {
        m_pendingAlarmSet = false;
    }

    if (status != QProcess::NormalExit || exitCode != 0) {
        logNetworkError(QStringLiteral("curl set"), QString::fromUtf8(err.isEmpty() ? out : err));
        m_netHintLabel->setText(QStringLiteral("curl 下发失败(code=%1)").arg(exitCode));
        return;
    }

    handleSetResponse(out, id);
}

void MainWidget::handleQueryResponse(const QByteArray &raw)
{
    if (raw.isEmpty()) {
        logNetworkError(QStringLiteral("query-device-property"), QStringLiteral("返回空数据"));
        return;
    }

    QJsonParseError err;
    const QJsonDocument doc = QJsonDocument::fromJson(raw, &err);
    if (err.error != QJsonParseError::NoError || !doc.isObject()) {
        logNetworkError(QStringLiteral("query-device-property"), err.errorString());
        return;
    }

    const QJsonObject root = doc.object();
    if (!isOneNetApiSuccess(root)) {
        const QString msg = root.value(QStringLiteral("msg")).toString();
        logNetworkError(QStringLiteral("query-device-property"), msg);
        m_netHintLabel->setText(QStringLiteral("平台错误：%1").arg(msg));
        return;
    }

    const QJsonArray list = extractPropertyList(root);
    if (list.isEmpty()) {
        m_netHintLabel->setText(QStringLiteral("已连接，等待设备上报属性..."));
    } else {
        parsePropertyList(list);
        m_netHintLabel->setText(QStringLiteral("同步成功 %1")
            .arg(QDateTime::currentDateTime().toString(QStringLiteral("hh:mm:ss"))));
    }

    refreshDataLabels();
    refreshIndicatorLabels();
    evaluateAutoAlarm();
    refreshAlarmBar();
}

void MainWidget::handleSetResponse(const QByteArray &raw, const QString &identifier)
{
    QJsonDocument doc = QJsonDocument::fromJson(raw);
    if (doc.isObject() && !isOneNetApiSuccess(doc.object())) {
        const QString msg = doc.object().value(QStringLiteral("msg")).toString();
        logNetworkError(QStringLiteral("set-device-property"), msg);
        m_netHintLabel->setText(QStringLiteral("下发失败：%1").arg(msg));
        return;
    }

    m_netHintLabel->setText(QStringLiteral("下发 %1 成功（设备需在线 MQTT 才能执行）").arg(identifier));
}

void MainWidget::onQueryFinished()
{
    QNetworkReply *reply = qobject_cast<QNetworkReply *>(sender());
    if (!reply) {
        return;
    }
    reply->deleteLater();

    if (reply->error() != QNetworkReply::NoError) {
        logNetworkError(QStringLiteral("query-device-property"), reply->errorString());
        m_netHintLabel->setText(QStringLiteral("网络异常(%1)：%2")
                                    .arg(reply->error())
                                    .arg(reply->errorString()));
        return;
    }

    handleQueryResponse(reply->readAll());
}

void MainWidget::onSetFinished()
{
    QNetworkReply *reply = qobject_cast<QNetworkReply *>(sender());
    if (!reply) {
        return;
    }
    const QString id = reply->property("setIdentifier").toString();
    reply->deleteLater();

    if (id == QLatin1String(PROP_ALARM)) {
        m_pendingAlarmSet = false;
    }

    if (reply->error() != QNetworkReply::NoError) {
        logNetworkError(QStringLiteral("set-device-property"), reply->errorString());
        return;
    }

    handleSetResponse(reply->readAll(), id);
}

// ============================================================
// JSON 解析
// ============================================================

bool MainWidget::parseBoolValue(const QString &raw, bool *out)
{
    if (!out) return false;
    const QString v = raw.trimmed().toLower();
    if (v == QLatin1String("true") || v == QLatin1String("1")) { *out = true; return true; }
    if (v == QLatin1String("false") || v == QLatin1String("0")) { *out = false; return true; }
    return false;
}

int MainWidget::parseIntValue(const QString &raw, bool *ok)
{
    return raw.trimmed().toInt(ok);
}

void MainWidget::parsePropertyList(const QJsonArray &list)
{
    int newTemp = m_temperature;
    int newHum  = m_humidity;
    bool gotTemp = false;
    bool gotHum  = false;

    for (const QJsonValue &v : list) {
        if (!v.isObject()) continue;
        const QJsonObject item = v.toObject();
        const QString id = item.value(QStringLiteral("identifier")).toString();

        // 兼容 value 为字符串 / 数字 / 布尔 / 嵌套对象
        QString valStr;
        const QJsonValue rawVal = item.value(QStringLiteral("value"));
        if (rawVal.isString()) {
            valStr = rawVal.toString();
        } else if (rawVal.isBool()) {
            valStr = rawVal.toBool() ? QStringLiteral("true") : QStringLiteral("false");
        } else if (rawVal.isDouble()) {
            valStr = QString::number(static_cast<int>(rawVal.toDouble()));
        } else if (rawVal.isObject()) {
            const QJsonObject vo = rawVal.toObject();
            if (vo.contains(QStringLiteral("value"))) {
                valStr = vo.value(QStringLiteral("value")).toVariant().toString();
            }
        }

        if (id == QLatin1String(PROP_TEMP)) {
            bool ok = false;
            const int t = parseIntValue(valStr, &ok);
            if (ok) { newTemp = qBound(0, t, 100); m_hasTemp = true; gotTemp = true; }
        } else if (id == QLatin1String(PROP_HUM)) {
            bool ok = false;
            const int h = parseIntValue(valStr, &ok);
            if (ok) { newHum = qBound(0, h, 100); m_hasHum = true; gotHum = true; }
        } else if (id == QLatin1String(PROP_LED)) {
            bool led = false;
            if (parseBoolValue(valStr, &led)) { m_ledOn = led; m_hasLed = true; }
        } else if (id == QLatin1String(PROP_ALARM)) {
            bool alarm = false;
            if (parseBoolValue(valStr, &alarm)) { m_alarmOn = alarm; m_hasAlarm = true; }
        }
    }

    m_temperature = newTemp;
    m_humidity = newHum;

    if (gotTemp && gotHum) {
        appendChartPoints(m_temperature, m_humidity);
    }
}

// ============================================================
// 阈值判断与自动蜂鸣器联动
// ============================================================

AlarmType MainWidget::checkThresholdAlarm() const
{
    if (!m_hasTemp || !m_hasHum) {
        return AlarmType::Normal;
    }
    const bool overT = m_temperature >= m_thresholdA;
    const bool overH = m_humidity >= m_thresholdB;
    if (overT && overH) return AlarmType::OverBoth;
    if (overT) return AlarmType::OverTemperature;
    if (overH) return AlarmType::OverHumidity;
    return AlarmType::Normal;
}

void MainWidget::evaluateAutoAlarm()
{
    if (!m_autoAlarmEnabled || !m_hasTemp || !m_hasHum) {
        return;
    }

    const AlarmType type = checkThresholdAlarm();
    const bool needOn  = (type != AlarmType::Normal);
    const bool needOff = (type == AlarmType::Normal);

    if (needOn && !m_alarmOn) {
        requestSetAlarm(true);
    } else if (needOff && m_alarmOn) {
        requestSetAlarm(false);
    }
}

void MainWidget::requestSetAlarm(bool on)
{
    if (m_pendingAlarmSet) return;
    m_pendingAlarmSet = true;
    m_alarmOn = on;
    refreshIndicatorLabels();
    setDeviceProperty(QString::fromLatin1(PROP_ALARM), on);
}

void MainWidget::requestSetLed(bool on)
{
    m_ledOn = on;
    refreshIndicatorLabels();
    setDeviceProperty(QString::fromLatin1(PROP_LED), on);
}

void MainWidget::onLedOnClicked()  { requestSetLed(true); }
void MainWidget::onLedOffClicked() { requestSetLed(false); }
void MainWidget::onAlarmOnClicked()  { requestSetAlarm(true); }
void MainWidget::onAlarmOffClicked() { requestSetAlarm(false); }
void MainWidget::onCloseClicked()    { close(); }

// ============================================================
// UI 刷新
// ============================================================

void MainWidget::refreshDataLabels()
{
    m_tempMainLabel->setText(m_hasTemp
        ? QStringLiteral("%1 ℃").arg(m_temperature)
        : QStringLiteral("-- ℃"));
    m_humMainLabel->setText(m_hasHum
        ? QStringLiteral("%1 %RH").arg(m_humidity)
        : QStringLiteral("-- %RH"));

    m_tempCompareLabel->setText(
        QStringLiteral("阈值 A：%1 ℃  |  %2")
            .arg(m_thresholdA)
            .arg(m_hasTemp && m_temperature >= m_thresholdA
                     ? QStringLiteral("已超限")
                     : QStringLiteral("正常")));
    m_humCompareLabel->setText(
        QStringLiteral("阈值 B：%1 %RH  |  %2")
            .arg(m_thresholdB)
            .arg(m_hasHum && m_humidity >= m_thresholdB
                     ? QStringLiteral("已超限")
                     : QStringLiteral("正常")));

    if (m_hasTemp && m_temperature >= m_thresholdA) {
        m_tempCompareLabel->setStyleSheet(QStringLiteral("color:#C62828;font-weight:bold;"));
    } else {
        m_tempCompareLabel->setStyleSheet(QStringLiteral("color:#607D8B;"));
    }
    if (m_hasHum && m_humidity >= m_thresholdB) {
        m_humCompareLabel->setStyleSheet(QStringLiteral("color:#C62828;font-weight:bold;"));
    } else {
        m_humCompareLabel->setStyleSheet(QStringLiteral("color:#607D8B;"));
    }
}

void MainWidget::refreshIndicatorLabels()
{
    auto setDot = [](QLabel *dot, const char *obj) {
        dot->setObjectName(QString::fromUtf8(obj));
        dot->style()->unpolish(dot);
        dot->style()->polish(dot);
    };

    if (!m_hasLed) {
        setDot(m_ledDotLabel, "dotOff");
        m_ledTextLabel->setText(QStringLiteral("LED：未知"));
    } else if (m_ledOn) {
        setDot(m_ledDotLabel, "dotOnGreen");
        m_ledTextLabel->setText(QStringLiteral("LED：已开启"));
    } else {
        setDot(m_ledDotLabel, "dotOff");
        m_ledTextLabel->setText(QStringLiteral("LED：已关闭"));
    }

    if (!m_hasAlarm) {
        setDot(m_alarmDotLabel, "dotOff");
        m_alarmTextLabel->setText(QStringLiteral("蜂鸣器：未知"));
    } else if (m_alarmOn) {
        setDot(m_alarmDotLabel, "dotOnRed");
        m_alarmTextLabel->setText(QStringLiteral("蜂鸣器：已开启"));
    } else {
        setDot(m_alarmDotLabel, "dotOff");
        m_alarmTextLabel->setText(QStringLiteral("蜂鸣器：已关闭"));
    }
}

void MainWidget::refreshAlarmBar()
{
    const AlarmType type = checkThresholdAlarm();

    if (type == AlarmType::Normal) {
        m_alarmBarLabel->setText(QStringLiteral("● 系统正常 · 温湿度均在设定阈值内"));
        m_alarmBarLabel->setObjectName(QStringLiteral("alarmBarNormal"));
        m_blinkTimer->stop();
    } else {
        QString text;
        switch (type) {
        case AlarmType::OverTemperature:
            text = QStringLiteral("⚠ 超温报警！当前 %1℃ ≥ 阈值 %2℃")
                       .arg(m_temperature).arg(m_thresholdA);
            break;
        case AlarmType::OverHumidity:
            text = QStringLiteral("⚠ 超湿报警！当前 %1%RH ≥ 阈值 %2%RH")
                       .arg(m_humidity).arg(m_thresholdB);
            break;
        case AlarmType::OverBoth:
            text = QStringLiteral("⚠ 双超限报警！温度 %1℃≥%2℃ 且 湿度 %3%RH≥%4%RH")
                       .arg(m_temperature).arg(m_thresholdA)
                       .arg(m_humidity).arg(m_thresholdB);
            break;
        default: break;
        }
        if (!m_autoAlarmEnabled) {
            text += QStringLiteral("（仅界面提示，未启用自动控制）");
        }
        m_alarmBarLabel->setText(text);
        m_alarmBarLabel->setObjectName(QStringLiteral("alarmBarWarnRed"));
        if (!m_blinkTimer->isActive()) {
            m_blinkRedPhase = true;
            m_blinkTimer->start();
        }
    }

    m_alarmBarLabel->style()->unpolish(m_alarmBarLabel);
    m_alarmBarLabel->style()->polish(m_alarmBarLabel);
}

void MainWidget::onBlinkTimerTimeout()
{
    if (checkThresholdAlarm() == AlarmType::Normal) {
        m_blinkTimer->stop();
        return;
    }
    m_blinkRedPhase = !m_blinkRedPhase;
    m_alarmBarLabel->setObjectName(m_blinkRedPhase
        ? QStringLiteral("alarmBarWarnRed")
        : QStringLiteral("alarmBarWarnGreen"));
    m_alarmBarLabel->style()->unpolish(m_alarmBarLabel);
    m_alarmBarLabel->style()->polish(m_alarmBarLabel);
}

void MainWidget::appendChartPoints(int temp, int hum)
{
    m_tempSeries->append(m_chartIndex, temp);
    m_humSeries->append(m_chartIndex, hum);
    ++m_chartIndex;

    auto trimSeries = [](QLineSeries *series) {
        if (series->count() > kMaxChartPoints) {
            series->removePoints(0, series->count() - kMaxChartPoints);
        }
    };
    trimSeries(m_tempSeries);
    trimSeries(m_humSeries);

    // 重排 X 轴使曲线从 0 连续滚动
    auto reindex = [](QLineSeries *series) {
        QVector<QPointF> pts;
        pts.reserve(series->count());
        for (int i = 0; i < series->count(); ++i) {
            pts.append(QPointF(i, series->at(i).y()));
        }
        series->replace(pts);
    };
    reindex(m_tempSeries);
    reindex(m_humSeries);
    m_chartIndex = m_tempSeries->count();

    // 直接使用 setupUi 中创建的 X 轴（Qt Charts 无 axis()，应使用 axes() 或保存指针）
    if (m_axisX) {
        m_axisX->setRange(0, qMax(kMaxChartPoints, m_chartIndex));
    }
}
