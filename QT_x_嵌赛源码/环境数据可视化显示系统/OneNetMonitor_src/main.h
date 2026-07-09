/**
 * @file main.h
 * @brief 应用程序全局常量与版本信息
 */

#ifndef MAIN_H
#define MAIN_H

/** 应用程序名称（窗口标题前缀） */
#define APP_NAME        "OneNET 物联网监控上位机"

/** 应用程序版本 */
#define APP_VERSION     "2.0.0"

/** 主窗口设计基准尺寸（全屏时会按屏幕等比缩放） */
#define APP_WIDTH       1150
#define APP_HEIGHT      750

/** 全局 UI 字体（Windows / ELF2 Linux 分别适配） */
#if defined(Q_OS_LINUX)
#  define APP_FONT_FAMILY "Noto Sans CJK SC"
#  define APP_FONT_FALLBACK "WenQuanYi Micro Hei, sans-serif"
#else
#  define APP_FONT_FAMILY "Microsoft YaHei"
#  define APP_FONT_FALLBACK "Microsoft YaHei, sans-serif"
#endif
#define APP_FONT_SIZE   10

#endif // MAIN_H
