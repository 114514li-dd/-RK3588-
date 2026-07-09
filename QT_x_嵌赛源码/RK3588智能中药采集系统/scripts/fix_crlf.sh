#!/bin/bash
# 修复从 Windows 共享文件夹复制来的 CRLF 换行问题
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if command -v dos2unix >/dev/null 2>&1; then
    find "$ROOT/scripts" -name '*.sh' -print0 | xargs -0 dos2unix
else
    find "$ROOT/scripts" -name '*.sh' -print0 | xargs -0 sed -i 's/\r$//'
fi

echo "已修复 scripts/*.sh 换行符 (CRLF -> LF)"
echo "请重新运行: bash scripts/fix_camera_linux.sh"
