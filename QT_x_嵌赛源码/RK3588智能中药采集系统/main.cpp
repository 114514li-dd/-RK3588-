#include "mainwindow.h"

#if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)
#include <QTextCodec>
#endif

#include "gouqiresult.h"
#include "objectrecognitionresult.h"

#include <QApplication>
#include <QLocale>

int main(int argc, char *argv[])
{
#if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)
    QTextCodec::setCodecForLocale(QTextCodec::codecForName("UTF-8"));
#endif

#ifdef Q_OS_LINUX
    qputenv("OPENCV_VIDEOIO_PRIORITY_LIST", "V4L2");
#endif

    QApplication app(argc, argv);
    QLocale::setDefault(QLocale(QLocale::Chinese, QLocale::China));

    qRegisterMetaType<GouqiRecognitionResult>("GouqiRecognitionResult");
    qRegisterMetaType<ObjectRecognitionResult>("ObjectRecognitionResult");
    QApplication::setAttribute(Qt::AA_EnableHighDpiScaling);
    app.setApplicationName(QStringLiteral("DrugRecognition"));
    app.setOrganizationName(QStringLiteral("RK3588"));

    MainWindow window;
    window.showFullScreen();

    return app.exec();
}
