/**
 * @file mainwidget.h
 * @brief OneNET 物模型监控主界面
 *
 * 模块划分：
 *   1. UI 布局与 QSS 样式（卡片、圆形指示灯、渐变背景）
 *   2. 网络请求封装（HTTP 轮询 / 属性下发）
 *   3. JSON 解析与设备数据缓存
 *   4. 阈值 cfg 本地持久化
 *   5. 阈值判断与自动蜂鸣器联动
 *   6. 报警栏红绿闪烁定时器
 *   7. 温湿度双折线图（Qt Charts）
 */

#ifndef MAINWIDGET_H
#define MAINWIDGET_H

#include <QWidget>
#include <QNetworkAccessManager>
#include <QNetworkRequest>
#include <QTimer>
#include <QProcess>
#include <QtCharts/QLineSeries>
#include <QtCharts/QChart>
#include <QtCharts/QChartView>
#include <QtCharts/QValueAxis>

QT_CHARTS_USE_NAMESPACE

QT_BEGIN_NAMESPACE
class QLabel;
class QLineEdit;
class QPushButton;
class QCheckBox;
class QNetworkReply;
class QResizeEvent;
class QShowEvent;
QT_END_NAMESPACE

/** @brief 报警类型，用于顶部提示栏文案 */
enum class AlarmType {
    Normal,
    OverTemperature,
    OverHumidity,
    OverBoth
};

class MainWidget : public QWidget
{
    Q_OBJECT

public:
    explicit MainWidget(QWidget *parent = nullptr);
    ~MainWidget() override;

protected:
    void resizeEvent(QResizeEvent *event) override;
    void showEvent(QShowEvent *event) override;

private slots:
    void onPollTimerTimeout();
    void onBlinkTimerTimeout();
    void onQueryFinished();
    void onSetFinished();
    void onSaveThresholdClicked();
    void onAutoAlarmToggled(bool checked);
    void onLedOnClicked();
    void onLedOffClicked();
    void onAlarmOnClicked();
    void onAlarmOffClicked();
    void onCloseClicked();
    void onCurlQueryFinished(int exitCode, QProcess::ExitStatus status);
    void onCurlSetFinished(int exitCode, QProcess::ExitStatus status);

private:
    // ---------- UI ----------
    void setupUi();
    void applyGlobalStyle();
    void applyUiScale();
    void applyCardShadow(QWidget *card);
    void connectSignals();

    // ---------- 本地 cfg 持久化 ----------
    QString cfgFilePath() const;
    void loadThresholdsFromCfg();
    void saveThresholdsToCfg();
    bool validateThresholdInput(QLineEdit *edit, int *outValue) const;

    // ---------- 网络请求封装 ----------
    void queryDeviceProperty();
    void setDeviceProperty(const QString &identifier, const QVariant &value);
    void applyApiHeaders(QNetworkRequest &request, bool isPost = true) const;
    void prepareNetworkReply(QNetworkReply *reply) const;
    void initNetworkBackend();
    static QString findCurlExecutable();
    static void ensureOpenSslDlls(const QString &appDir);
    void queryDevicePropertyViaCurl();
    void setDevicePropertyViaCurl(const QString &identifier, const QVariant &value);
    void handleQueryResponse(const QByteArray &raw);
    void handleSetResponse(const QByteArray &raw, const QString &identifier);
    QString apiBaseUrl() const;
    void logNetworkError(const QString &action, const QString &detail) const;

    // ---------- JSON 解析 ----------
    void parsePropertyList(const QJsonArray &list);
    static bool parseBoolValue(const QString &raw, bool *out);
    static int  parseIntValue(const QString &raw, bool *ok);

    // ---------- 阈值判断与报警 ----------
    AlarmType checkThresholdAlarm() const;
    void evaluateAutoAlarm();
    void requestSetAlarm(bool on);
    void requestSetLed(bool on);

    // ---------- UI 刷新 ----------
    void refreshDataLabels();
    void refreshIndicatorLabels();
    void refreshAlarmBar();
    void appendChartPoints(int temp, int hum);

    // ---------- 网络 ----------
    QNetworkAccessManager *m_networkManager;
    QTimer *m_pollTimer;
    QTimer *m_blinkTimer;
    bool m_blinkRedPhase;
    bool m_useCurlBackend;
    bool m_curlQueryBusy;
    QString m_curlPath;

    // ---------- 设备数据 ----------
    int  m_temperature;
    int  m_humidity;
    bool m_ledOn;
    bool m_alarmOn;
    bool m_hasTemp;
    bool m_hasHum;
    bool m_hasLed;
    bool m_hasAlarm;

    // ---------- 阈值 ----------
    int  m_thresholdA;
    int  m_thresholdB;
    bool m_autoAlarmEnabled;
    bool m_pendingAlarmSet;

    // ---------- 折线图 ----------
    QLineSeries *m_tempSeries;
    QLineSeries *m_humSeries;
    QChart *m_chart;
    QChartView *m_chartView;
    QValueAxis *m_axisX;
    int m_chartIndex;
    qreal m_uiScale;

    // ---------- UI 控件 ----------
    QLabel *m_titleLabel;
    QLabel *m_alarmBarLabel;
    QLabel *m_tempMainLabel;
    QLabel *m_tempCompareLabel;
    QLabel *m_humMainLabel;
    QLabel *m_humCompareLabel;
    QLabel *m_ledDotLabel;
    QLabel *m_ledTextLabel;
    QLabel *m_alarmDotLabel;
    QLabel *m_alarmTextLabel;
    QLabel *m_netHintLabel;
    QLineEdit *m_thresholdAEdit;
    QLineEdit *m_thresholdBEdit;
    QCheckBox *m_autoAlarmCheck;
    QPushButton *m_saveThresholdBtn;
    QPushButton *m_ledOnBtn;
    QPushButton *m_ledOffBtn;
    QPushButton *m_alarmOnBtn;
    QPushButton *m_alarmOffBtn;
    QPushButton *m_closeBtn;
};

#endif // MAINWIDGET_H
