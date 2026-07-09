#ifndef AIINFERENCETHREAD_H
#define AIINFERENCETHREAD_H

#include "gouqiresult.h"
#include "objectrecognitionresult.h"

#include <QThread>

/**
 * @brief AI 推理线程
 * 调用本地 DeepSeek 推理程序，支持枸杞识别与通用识物两种模式。
 */
class AIInferenceThread : public QThread
{
    Q_OBJECT

public:
    enum InferenceMode {
        GouqiMode = 0,
        ObjectMode = 1
    };

    explicit AIInferenceThread(QObject *parent = 0);

    void setProgramPath(const QString &programPath);
    QString programPath() const;
    static QString resolveProgramPath(const QString &configuredPath);
    static bool isDemoInferScript(const QString &programPath);

public slots:
    void startInference(const QString &imagePath, InferenceMode mode = GouqiMode);

signals:
    void inferenceStarted();
    void inferenceFinished(const GouqiRecognitionResult &result);
    void objectInferenceFinished(const ObjectRecognitionResult &result);
    void inferenceFailed(const QString &errorMessage);

protected:
    void run() override;

private:
    bool ensureInferScriptAvailable(const QString &programPath) const;

    QString m_programPath;
    QString m_imagePath;
    InferenceMode m_mode;
};

#endif // AIINFERENCETHREAD_H
