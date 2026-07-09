/**
 * @file main.cpp
 * @brief 程序入口：初始化 QApplication 并显示主窗口
 */

#include "main.h"
#include "mainwidget.h"

#include <QApplication>
#include <QCoreApplication>
#include <QFont>
#include <QFontDatabase>
#include <QSslSocket>

#if defined(Q_OS_WIN)
#include <QLibrary>
#include <Windows.h>

/** Windows Qt5.8：预加载 OpenSSL 1.0 DLL 以启用 HTTPS */
static void preloadOpenSsl(const QString &appDir)
{
    QCoreApplication::addLibraryPath(appDir);
    SetDllDirectoryW(reinterpret_cast<LPCWSTR>(appDir.utf16()));
    QLibrary(appDir + QStringLiteral("/libeay32.dll")).load();
    QLibrary(appDir + QStringLiteral("/ssleay32.dll")).load();
}
#endif

/** Linux/ELF2：优先加载系统中文字体 */
static void setupPlatformFont(QApplication &app)
{
#if defined(Q_OS_LINUX)
    const QStringList candidates = {
        QStringLiteral(APP_FONT_FAMILY),
        QStringLiteral("WenQuanYi Micro Hei"),
        QStringLiteral("Source Han Sans CN"),
        QStringLiteral("Droid Sans Fallback")
    };
    for (const QString &family : candidates) {
        if (QFontDatabase().hasFamily(family)) {
            QFont font(family);
            font.setPointSize(APP_FONT_SIZE);
            app.setFont(font);
            return;
        }
    }
#endif
    QFont font(QStringLiteral(APP_FONT_FAMILY));
    font.setPointSize(APP_FONT_SIZE);
    app.setFont(font);
}

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
#if defined(Q_OS_WIN)
    preloadOpenSsl(app.applicationDirPath());
#endif

    app.setApplicationName(QStringLiteral(APP_NAME));
    app.setApplicationVersion(QStringLiteral(APP_VERSION));
    setupPlatformFont(app);

    MainWidget w;
    w.showFullScreen();

    return app.exec();
}
