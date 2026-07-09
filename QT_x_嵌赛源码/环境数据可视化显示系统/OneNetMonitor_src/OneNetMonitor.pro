#-------------------------------------------------
# OneNET 物模型 Qt 物联网监控上位机
# 兼容 Qt5 / Qt6；Windows 桌面 + ELF2(RK3588) Linux
# 依赖：core gui network widgets charts
#-------------------------------------------------

QT       += core gui network charts

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

CONFIG   += c++11

TARGET   = OneNetMonitor
TEMPLATE = app

SOURCES += \
    main.cpp \
    mainwidget.cpp

HEADERS += \
    main.h \
    mainwidget.h

# ---------- Windows 桌面 ----------
win32:msvc* {
    QMAKE_CXXFLAGS += /utf-8
}

# Qt 5.8 MinGW 默认不带 OpenSSL，HTTPS 会失败；编译后自动复制 DLL 到 exe 目录
win32-g++ {
    exists(C:/Qt/Qt5.8.0/Tools/QtCreator/bin/libeay32.dll) {
        SSL_DLL_DIR = C:/Qt/Qt5.8.0/Tools/QtCreator/bin
    } else:exists($$[QT_INSTALL_PREFIX]/../../Tools/QtCreator/bin/libeay32.dll) {
        SSL_DLL_DIR = $$[QT_INSTALL_PREFIX]/../../Tools/QtCreator/bin
    }
    !isEmpty(SSL_DLL_DIR) {
        QMAKE_POST_LINK += $$quote(cmd /c copy /Y \"$$SSL_DLL_DIR\\libeay32.dll\" \"$$OUT_PWD\\\") &
        QMAKE_POST_LINK += $$quote(cmd /c copy /Y \"$$SSL_DLL_DIR\\ssleay32.dll\" \"$$OUT_PWD\\\") &
    }
}

# ---------- ELF2 / RK3588 嵌入式 Linux ----------
unix:!macx {
    DEFINES += ELF2_RK3588
    QMAKE_CXXFLAGS += -Wall
    # 链接 OpenSSL，确保 QNetworkAccessManager HTTPS 可用
    LIBS += -lssl -lcrypto
    # 交叉编译时可指定 sysroot：qmake SYSROOT=/path/to/sysroot
    !isEmpty(SYSROOT) {
        QMAKE_CFLAGS   += --sysroot=$$SYSROOT
        QMAKE_CXXFLAGS += --sysroot=$$SYSROOT
        QMAKE_LFLAGS   += --sysroot=$$SYSROOT
        LIBS += -L$$SYSROOT/usr/lib -L$$SYSROOT/lib
    }
}
