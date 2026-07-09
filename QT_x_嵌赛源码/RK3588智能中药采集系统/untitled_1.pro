#-------------------------------------------------
# Drug Recognition System - Cross-platform Qt Project
# Windows (MinGW) + Linux (Ubuntu/Debian/RK3588)
#-------------------------------------------------

QT += core gui widgets

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = drug_recognition
TEMPLATE = app

DEFINES += QT_DEPRECATED_WARNINGS

CONFIG += c++11

# Release 优化（Linux 板端推荐）
contains(CONFIG, release): DEFINES += QT_NO_DEBUG_OUTPUT

SOURCES += \
    main.cpp \
    mainwindow.cpp \
    camerathread.cpp \
    aiinferencethread.cpp \
    imagepreprocessor.cpp \
    gouqiprompt.cpp \
    gouqiparser.cpp \
    gouqiresult.cpp \
    gouqiimageanalyzer.cpp \
    objectprompt.cpp \
    objectparser.cpp \
    objectrecognitionresult.cpp \
    nativevisionrecognizer.cpp \
    platformpaths.cpp \
    buildconfig.cpp \
    herbdetection.cpp \
    previewlabel.cpp

HEADERS += \
    mainwindow.h \
    camerathread.h \
    aiinferencethread.h \
    imagepreprocessor.h \
    gouqiprompt.h \
    gouqiparser.h \
    gouqiresult.h \
    gouqiimageanalyzer.h \
    objectprompt.h \
    objectparser.h \
    objectrecognitionresult.h \
    nativevisionrecognizer.h \
    platformpaths.h \
    buildconfig.h \
    herbdetection.h \
    previewlabel.h

FORMS += mainwindow.ui

RESOURCES += resources.qrc

# ---------- 构建后复制推理脚本到可执行文件旁 ----------
win32 {
    SCRIPTS_OUT = $$shell_path($$OUT_PWD/scripts)
    BAT_SRC = $$shell_path($$PWD/scripts/deepseek_infer.bat)
    PY_SRC = $$shell_path($$PWD/scripts/object_recognize.py)
    QMAKE_POST_LINK += $$escape_expand(\\n\\t) if not exist \"$$SCRIPTS_OUT\" mkdir \"$$SCRIPTS_OUT\"
    QMAKE_POST_LINK += $$escape_expand(\\n\\t) if exist \"$$BAT_SRC\" copy /Y \"$$BAT_SRC\" \"$$SCRIPTS_OUT\\\"
    QMAKE_POST_LINK += $$escape_expand(\\n\\t) if exist \"$$PY_SRC\" copy /Y \"$$PY_SRC\" \"$$SCRIPTS_OUT\\\"
}

unix:!macx {
    SCRIPTS_OUT = $$shell_path($$OUT_PWD/scripts)
    SH_SRC = $$shell_path($$PWD/scripts/deepseek_infer.sh)
    PY_SRC = $$shell_path($$PWD/scripts/object_recognize.py)
    QMAKE_POST_LINK += $$escape_expand(\\n\\t) mkdir -p \"$$SCRIPTS_OUT\"
    QMAKE_POST_LINK += $$escape_expand(\\n\\t) cp -f \"$$SH_SRC\" \"$$SCRIPTS_OUT/\"
    QMAKE_POST_LINK += $$escape_expand(\\n\\t) cp -f \"$$PY_SRC\" \"$$SCRIPTS_OUT/\"
    QMAKE_POST_LINK += $$escape_expand(\\n\\t) chmod +x \"$$SCRIPTS_OUT/deepseek_infer.sh\"
}

# ---------- OpenCV / 摄像头 ----------
win32 {
    # 使用 ElfBoard USB 摄像头时推荐取消下行注释并设置 OpenCV 路径：
    # OPENCV_DIR = C:/opencv/build

    OPENCV_ENABLED = false

    !isEmpty(OPENCV_DIR) {
        exists($$OPENCV_DIR/include/opencv2/opencv.hpp) {
            DEFINES += HAS_OPENCV
            OPENCV_ENABLED = true
            INCLUDEPATH += $$OPENCV_DIR/include

            exists($$OPENCV_DIR/x64/mingw/lib/libopencv_world*.a) {
                LIBS += -L$$OPENCV_DIR/x64/mingw/lib -lopencv_world480
            } else:exists($$OPENCV_DIR/x86/mingw/lib/libopencv_world*.a) {
                LIBS += -L$$OPENCV_DIR/x86/mingw/lib -lopencv_world480
            } else:exists($$OPENCV_DIR/x64/vc15/lib/opencv_world*.lib) {
                CONFIG(debug, debug|release) {
                    LIBS += -L$$OPENCV_DIR/x64/vc15/lib -lopencv_world480d
                } else {
                    LIBS += -L$$OPENCV_DIR/x64/vc15/lib -lopencv_world480
                }
            } else {
                OPENCV_ENABLED = false
                warning("OpenCV libs not found under OPENCV_DIR, fallback to Qt Multimedia")
            }
        } else {
            warning("Invalid OPENCV_DIR, fallback to Qt Multimedia")
        }
    }

    equals(OPENCV_ENABLED, false) {
        QT += multimedia
        DEFINES += USE_QT_CAMERA
        message("Windows: using Qt Multimedia camera (USB webcam)")
        message("Tip: set OPENCV_DIR for ElfBoard USB camera via OpenCV")
    } else {
        message("Windows: OpenCV USB camera enabled")
    }
}

unix:!macx {
    CONFIG += link_pkgconfig
    LIBS += -lpthread

    # 检测交叉编译（Qt Creator RK3588/Buildroot 套件）
    CROSS_COMPILE = false
    contains(CONFIG, native_build) {
        CROSS_COMPILE = false
    } else:contains(QMAKE_CXX, aarch64)|contains(QMAKE_CC, aarch64)|contains(QMAKE_CXX, buildroot) {
        CROSS_COMPILE = true
    }

    OPENCV_ENABLED = false

    equals(CROSS_COMPILE, true) {
        message("Cross-compile mode detected")
        !isEmpty(OPENCV_DIR) {
            exists($$OPENCV_DIR/include/opencv4/opencv2/opencv.hpp)|exists($$OPENCV_DIR/include/opencv2/opencv.hpp) {
                DEFINES += HAS_OPENCV
                OPENCV_ENABLED = true
                INCLUDEPATH += $$OPENCV_DIR/include $$OPENCV_DIR/include/opencv4
                LIBS += -L$$OPENCV_DIR/lib \
                        -lopencv_core -lopencv_imgproc -lopencv_videoio -lopencv_imgcodecs
                message("Cross: OpenCV from OPENCV_DIR=$$OPENCV_DIR")
            }
        }
        equals(OPENCV_ENABLED, false) {
            warning("Cross-compile: set OPENCV_DIR to sysroot OpenCV path")
            warning("Example: qmake OPENCV_DIR=/path/to/sysroot/usr")
        }
    } else {
        packagesExist(opencv4) {
            DEFINES += HAS_OPENCV
            OPENCV_ENABLED = true
            PKGCONFIG += opencv4
            message("Linux native: OpenCV4 via pkg-config")
        } else:packagesExist(opencv) {
            DEFINES += HAS_OPENCV
            OPENCV_ENABLED = true
            PKGCONFIG += opencv
            message("Linux native: OpenCV via pkg-config")
        } else:!isEmpty(OPENCV_DIR) {
            exists($$OPENCV_DIR/include/opencv4/opencv2/opencv.hpp)|exists($$OPENCV_DIR/include/opencv2/opencv.hpp) {
                DEFINES += HAS_OPENCV
                OPENCV_ENABLED = true
                INCLUDEPATH += $$OPENCV_DIR/include $$OPENCV_DIR/include/opencv4
                LIBS += -L$$OPENCV_DIR/lib \
                        -lopencv_core -lopencv_imgproc -lopencv_videoio -lopencv_imgcodecs
                message("Linux native: OpenCV via OPENCV_DIR")
            }
        } else:exists(/usr/include/opencv4/opencv2/opencv.hpp) {
            DEFINES += HAS_OPENCV
            OPENCV_ENABLED = true
            INCLUDEPATH += /usr/include/opencv4
            LIBS += -lopencv_core -lopencv_imgproc -lopencv_videoio -lopencv_imgcodecs
            message("Linux native: OpenCV4 from /usr/include/opencv4")
        } else:exists(/usr/include/opencv2/opencv.hpp) {
            DEFINES += HAS_OPENCV
            OPENCV_ENABLED = true
            INCLUDEPATH += /usr/include/opencv
            LIBS += -lopencv_core -lopencv_imgproc -lopencv_videoio -lopencv_imgcodecs
            message("Linux native: OpenCV from /usr/include/opencv2")
        }

        LIB_SEARCH_PATHS = /usr/lib/x86_64-linux-gnu /usr/lib/aarch64-linux-gnu /usr/lib/arm-linux-gnueabihf /usr/lib
        for(libpath, LIB_SEARCH_PATHS) {
            equals(OPENCV_ENABLED, false) {
                exists($$libpath/libopencv_core.so)|exists($$libpath/libopencv_core.so.*) {
                    DEFINES += HAS_OPENCV
                    OPENCV_ENABLED = true
                    exists(/usr/include/opencv4/opencv2/opencv.hpp) {
                        INCLUDEPATH += /usr/include/opencv4
                    } else {
                        INCLUDEPATH += /usr/include/opencv2
                    }
                    LIBS += -L$$libpath -lopencv_core -lopencv_imgproc -lopencv_videoio -lopencv_imgcodecs
                    message("Linux native: OpenCV libs in $$libpath")
                }
            }
        }
    }

    equals(OPENCV_ENABLED, false) {
        warning("Linux: OpenCV not found - camera disabled")
        warning("Native VM: sudo apt install libopencv-dev && bash scripts/fix_camera_linux.sh")
        warning("Cross board: qmake OPENCV_DIR=/path/to/sysroot/usr")
    } else {
        message("Linux: OpenCV camera enabled")
    }
}

# ---------- 可选：make install 安装到系统 ----------
unix:!macx {
    isEmpty(PREFIX): PREFIX = /usr/local
    target.path = $$PREFIX/bin
    INSTALLS += target

    deploy_scripts.files = $$PWD/scripts/deepseek_infer.sh $$PWD/scripts/object_recognize.py
    deploy_scripts.path = $$PREFIX/share/drug_recognition/scripts
    INSTALLS += deploy_scripts
}

# RK3588 交叉编译示例:
# qmake CONFIG+=release \
#   QMAKE_CC=aarch64-linux-gnu-gcc QMAKE_CXX=aarch64-linux-gnu-g++ \
#   OPENCV_DIR=/path/to/sysroot/usr
