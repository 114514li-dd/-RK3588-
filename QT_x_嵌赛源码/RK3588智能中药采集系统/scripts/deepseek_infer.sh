#!/bin/bash
# DeepSeek 本地推理脚本
# 用法: ./deepseek_infer.sh --image /path/to.jpg --prompt-file /path/to/prompt.txt [--mode object|gouqi]

IMAGE=""
PROMPT_FILE=""
MODE="gouqi"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --image)
            IMAGE="$2"
            shift 2
            ;;
        --prompt-file)
            PROMPT_FILE="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        *)
            echo "未知参数: $1" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$IMAGE" || ! -f "$IMAGE" ]]; then
    echo "图片不存在: $IMAGE" >&2
    exit 2
fi

if [[ -n "$PROMPT_FILE" && ! -f "$PROMPT_FILE" ]]; then
    echo "提示词文件不存在: $PROMPT_FILE" >&2
    exit 3
fi

# TODO: 替换为真实 DeepSeek 视觉推理
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ -z "$PROMPT_FILE" ]]; then
    if [[ "$MODE" == "object" ]]; then
        DEFAULT_PROMPT="$SCRIPT_DIR/../prompts/object_recognition.txt"
    else
        DEFAULT_PROMPT="$SCRIPT_DIR/../prompts/gouqi_recognition.txt"
    fi

    if [[ -f "$DEFAULT_PROMPT" ]]; then
        PROMPT_FILE="$DEFAULT_PROMPT"
        echo "未提供提示词文件，使用默认提示词: $PROMPT_FILE" >&2
    else
        echo "未提供提示词文件，且未找到默认提示词文件。" >&2
    fi
fi

if [[ "$MODE" == "object" ]]; then
    PY_SCRIPT="$SCRIPT_DIR/object_recognize.py"
    if command -v python3 >/dev/null 2>&1 && [[ -f "$PY_SCRIPT" ]]; then
        python3 "$PY_SCRIPT" "$IMAGE"
        exit $?
    fi
    echo "【识别失败】未找到 object_recognize.py 或未安装 python3。"
    echo "【详细描述】请在板端执行: sudo apt install python3-opencv，并确认 scripts 目录完整。"
    exit 0
fi

echo "【药品名称】宁夏枸杞（Lycium barbarum L.）"
echo "【药材分类】补阴药"
echo "【性味归经】甘，平。归肝、肾经"
echo "【功效】滋补肝肾，益精明目"
echo "【用法用量】6-12g，煎服；也可泡水、煲汤"
echo "【禁忌】脾虚便溏者慎用"
echo "【真伪鉴别要点】纺锤形或椭圆形，表面暗红色，具不规则皱纹，一端可见花柱残迹"
echo "【温度】10~20°C"
echo "【相对湿度】45~60%"
