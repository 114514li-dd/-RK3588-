#!/usr/bin/env bash
# 将编译产物与 scripts 部署到指定目录（默认 ~/drug_recognition）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="${1:-$ROOT/build-linux}"
DEPLOY_DIR="${2:-$HOME/drug_recognition}"

if [[ ! -f "$BUILD_DIR/drug_recognition" ]]; then
    echo "未找到可执行文件: $BUILD_DIR/drug_recognition"
    echo "请先运行: bash scripts/build_linux.sh"
    exit 1
fi

mkdir -p "$DEPLOY_DIR/scripts"
install -m 755 "$BUILD_DIR/drug_recognition" "$DEPLOY_DIR/"
install -m 755 "$ROOT/scripts/deepseek_infer.sh" "$DEPLOY_DIR/scripts/"
install -m 644 "$ROOT/scripts/object_recognize.py" "$DEPLOY_DIR/scripts/"

echo "已部署到: $DEPLOY_DIR"
echo "启动: cd $DEPLOY_DIR && ./drug_recognition"
