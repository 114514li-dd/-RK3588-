# 飞凌 ELF2 (RK3588) 部署指南 — 白芷 / 枸杞

将 Windows 上训练好的 YOLOv8 模型部署到 **飞凌 ELF2 (RK3588)** 板端 NPU 推理。

官方资料（你本地路径）：

- **快速使用手册**：`d:\ELF2资源包\01-教程文档\ELF 2开发板快速使用手册\ELF 2开发板快速使用手册.pdf`
- **AI 训练到部署例程**：`d:\ELF2资源包\01-教程文档\进阶篇之-基于RK3588的AI模型训练到部署\`
- **Ubuntu 开发环境 VM**：`d:\ELF2资源包\1\08-开发环境\elf2_Ubuntu22.04\`（账户 `elf` / 密码 `elf`，已含 RKNN-Toolkit2 2.1.0 与 2.3.2）

## 架构概览

```
Windows PC (Ultralytics 训练 + 摄像头验证)
    │  best.pt
    ▼
WSL2 / 飞凌 Ubuntu VM (RKNN-Toolkit2 量化导出)
    │  *.rknn
    ▼
ELF2 板端 (rknnlite2 + NPU)
    │  UVC /dev/video21 或 MIPI 摄像头
    ▼
  检测框输出
```

> **重要**：RKNN 转换必须在 **x86 Linux**（WSL 或飞凌提供的 Ubuntu 虚拟机）完成，不能在 Windows 直接转，也不能在 RK3588 板上转。

---

## 一、ELF2 板端准备（对照手册）

### 1. 登录方式（手册第 2 章）

| 方式 | 说明 |
|------|------|
| **串口** | Type-C 调试口，115200 8N1；用户 `elf`/`elf` 或 `root`/`root` |
| **SSH** | `ssh elf@192.168.0.232`（Buildroot 出厂 eth0 常为静态 **192.168.0.232**） |
| **SFTP** | FileZilla，用户 `elf`，密码 `elf`，传模型与 `rk3588/` 目录 |

Desktop 镜像默认 **DHCP** 获取 IP，需 `ifconfig` 查看实际地址。

### 2. NPU 是否正常（手册 3.1.21）

Buildroot 系统可先做官方测试：

```bash
/usr/bin/rknn_common_test \
  /usr/share/model/RK3588/mobilenet_v1.rknn \
  /usr/share/model/dog_224x224.jpg
```

正常输出应包含 `driver version: 0.9.8`（手册 V1.1 已升级 NPU 驱动）及 Top5 分类结果。  
若此步失败，请先排查 RKNPU2 驱动，再跑本项目推理。

### 3. 版本兼容（手册第 4 章 Desktop 说明）

| 系统 | RKNPU2 / 驱动 | 建议 |
|------|----------------|------|
| **Buildroot**（默认出厂） | rknnrt + 驱动 **0.9.8** | PC 端用 **RKNN-Toolkit2 2.3.2** 导出（本仓库 `export_models_wsl.sh`） |
| **Desktop** | 预装 RKNPU2 **2.1.0**，驱动 0.9.6 | 保持 Toolkit2 / Lite2 **2.1.0** 一致，勿随意混用版本 |

Toolkit2 与板端 RKNPU2 版本不一致时，可能出现 `load_rknn` / `init_runtime` 失败。

### 4. 板端依赖安装

SSH 登录板子后：

```bash
cd ~/ultralytics-main   # 或你的项目路径
bash rk3588/setup_board.sh
```

脚本会检查 `/dev/rknpu`、可选运行 `rknn_common_test`、列出摄像头设备，并安装 OpenCV / PyYAML 等。

**rknnlite2** 需从飞凌资料包或 Rockchip SDK 安装与系统匹配的 whl，例如：

```bash
pip3 install rknnlite2-2.3.0-cp310-cp310-linux_aarch64.whl
pip3 install numpy opencv-python-headless pyyaml
```

板端 **不需要** PyTorch、CUDA、完整 ultralytics。

---

## 二、PC 端导出 RKNN

### 方式 A：Windows 双击（WSL2）

```bat
启动RK3588导出.bat
```

### 方式 B：WSL / 飞凌 Ubuntu VM 手动

```bash
cd /path/to/ultralytics-main
bash rk3588/export_models_wsl.sh
```

输出：

```
rk3588/artifacts/gouqi_yolov8s_ca_rk3588.rknn
rk3588/artifacts/baizhi_yolov8s_ca_rk3588.rknn
```

WSL 需：`pip install ultralytics rknn-toolkit2>=2.3.2 "onnx<1.19.0"`

飞凌 VM 中若使用 2.1.0 工具链，请在 **Desktop 镜像** 板子上配套 2.1.0 重新导出，或统一升级板端 RKNPU2 栈。

---

## 三、拷贝到 ELF2

```bash
scp -r rk3588 elf@192.168.0.232:~/ultralytics-main/
# 或 SFTP 上传整个 rk3588 目录（含 artifacts/*.rknn）
```

---

## 四、摄像头（手册 3.3.4）

ELF2 支持 **UVC USB 摄像头** 与 **OV13855 MIPI**。

1. 查设备：

```bash
v4l2-ctl --list-devices
v4l2-ctl --list-formats-ext -d /dev/video21   # UVC 常见节点
```

2. 官方 AI 例程默认 UVC：**`/dev/video21`**（见资料包 `main_camera_fps_v8.py`）。

3. 本项目默认已在 `deploy.yaml` 中设置：

```yaml
inference:
  camera: "/dev/video21"
```

若你的设备不同，改此字段或用命令行覆盖：

```bash
python3 rk3588/infer_camera.py --herb gouqi --camera /dev/video0
```

Buildroot 环境变量 `GST_V4L2SRC_DEFAULT_DEVICE=/dev/video-camera0` 仅影响 GStreamer，OpenCV 仍需指定正确 `/dev/videoX`。

---

## 五、板端运行

| Windows | ELF2 |
|---------|------|
| `启动枸杞检测.bat` | `bash rk3588/启动枸杞检测.sh` |
| `启动白芷检测.bat` | `bash rk3588/启动白芷检测.sh` |
| `启动白芷枸杞检测.bat` | `bash rk3588/启动白芷枸杞检测.sh` |

```bash
bash rk3588/启动枸杞检测.sh
bash rk3588/启动白芷检测.sh
bash rk3588/启动白芷枸杞检测.sh

# 单张图片
python3 rk3588/infer_camera.py --herb baizhi --source test.jpg --save out.jpg
```

检测阈值见 `rk3588/deploy.yaml`（白芷 conf≥0.50、连续 2 帧确认等，与 Windows 一致）。

---

## 六、VS Code Remote-SSH

1. 扩展 **Remote - SSH**
2. 连接 `elf@192.168.0.232`（或 Desktop 实际 IP）
3. 打开 `~/ultralytics-main`
4. 终端执行 `bash rk3588/启动枸杞检测.sh`
5. 需板端接 HDMI/屏幕才能 `cv2.imshow`；无屏时用 `--source` 测图

---

## 七、常见问题

| 现象 | 处理 |
|------|------|
| `ImportError: rknnlite2` | 安装与 RKNPU2 版本匹配的 whl |
| `load_rknn failed` | 确认 `.rknn` 为 **rk3588** 导出；Toolkit2 与板端 RKNPU2 版本一致 |
| `init_runtime failed` | 检查 `/dev/rknpu`；先跑 `rknn_common_test` |
| 摄像头打不开 | `v4l2-ctl --list-devices`，改 `deploy.yaml` 的 `camera` |
| 帧率低 | 增大 `infer_every`；参考官方 `rknnPoolExecutor` 多 NPU 线程（进阶篇 demo） |
| 误检 / 漏检 | 调 `deploy.yaml` 的 `conf`、`confirm_frames`；或 Windows 侧补实拍再训练 |

---

## 八、目录结构

```
rk3588/
├── README.md              # 本文档
├── deploy.yaml            # 板端参数（含 ELF2 默认 camera）
├── setup_board.sh         # 板端环境 + NPU/摄像头自检
├── export_models_wsl.sh   # PC/WSL 导出 RKNN
├── infer_camera.py        # 统一推理入口
├── yolov8_postprocess.py  # YOLOv8 后处理
├── artifacts/             # 放置 *.rknn
├── 启动枸杞检测.sh
├── 启动白芷检测.sh
└── 启动白芷枸杞检测.sh
```

与 `baizhi/elf2/` 的关系：`baizhi/elf2/board_infer.py` 为早期白芷单类脚本；**推荐统一使用本目录** 的 `infer_camera.py` 跑枸杞/白芷/双类。
