#!/bin/bash
set -euo pipefail

APP_NAME="drug_recognition"
APP_DIR="/opt/drug_recognition"
SCRIPT_DIR="/opt/drug_recognition/scripts"

sudo mkdir -p "$APP_DIR" "$SCRIPT_DIR"

if [ $# -gt 0 ]; then
    SRC_APP="$1"
else
    SRC_APP="$(cd "$(dirname "$0")/.." && pwd)/build-aarch64/$APP_NAME"
fi

if [ ! -f "$SRC_APP" ]; then
    echo "错误: 未找到可执行文件: $SRC_APP"
    echo "请先运行 scripts/build_cross_aarch64.sh"
    exit 1
fi

sudo cp -f "$SRC_APP" "$APP_DIR/$APP_NAME"
sudo cp -f "$(cd "$(dirname "$0")" && pwd)/deepseek_infer.sh" "$SCRIPT_DIR/"
sudo cp -f "$(cd "$(dirname "$0")" && pwd)/object_recognize.py" "$SCRIPT_DIR/"
sudo chmod +x "$APP_DIR/$APP_NAME" "$SCRIPT_DIR/deepseek_infer.sh" "$SCRIPT_DIR/object_recognize.py"

sudo mkdir -p /usr/share/drug_recognition/scripts
sudo cp -f "$SCRIPT_DIR/deepseek_infer.sh" /usr/share/drug_recognition/scripts/
sudo cp -f "$SCRIPT_DIR/object_recognize.py" /usr/share/drug_recognition/scripts/

echo "部署完成："
echo "  可执行文件: $APP_DIR/$APP_NAME"
echo "  脚本目录: $SCRIPT_DIR"
echo "运行示例："
echo "  sudo chmod 755 $APP_DIR/$APP_NAME"
echo "  $APP_DIR/$APP_NAME"
