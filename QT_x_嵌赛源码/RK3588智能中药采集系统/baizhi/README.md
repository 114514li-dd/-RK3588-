# 白芷单类别目标检测工程 (YOLOv8s + C2fCA → RK3588)

> 识别目标：白芷（class id = 0），含新鲜根 / 干药材 / 饮片切片三种形态  
> 部署平台：瑞芯微 RK3588 (INT8 RKNN)

---

## 一、工程目录结构

```
baizhi/
├── cfg/
│   ├── yolov8s-ca.yaml          # C2f+CA 模型结构 (nc=1)
│   └── shape_priors.yaml        # anchor_kmeans.py 生成（训练后）
├── dataset/
│   ├── data.yaml                # 数据集配置
│   ├── images/
│   │   ├── train/               # 训练图片
│   │   └── val/                 # 验证图片
│   └── labels/
│       ├── train/               # YOLO 标注 (.txt)
│       └── val/
├── scripts/
│   ├── train.py                 # 训练
│   ├── detect_image.py          # 单图推理（中文标签）
│   ├── detect_camera.py         # 摄像头实时检测
│   ├── anchor_kmeans.py         # 框形 K-means 聚类
│   ├── export_rknn.py           # RKNN 导出
│   ├── rk3588_infer.py          # 板端推理示例
│   └── utils_plot.py            # 中文框绘制
├── runs/detect/                 # 训练输出
└── weights/rknn/                # RKNN 模型
```

---

## 二、数据集规范与标注要求

### 2.1 类别定义

| class id | 英文名 | 中文名 | 形态说明 |
|----------|--------|--------|----------|
| 0 | baizhi | 白芷 | 三种形态统一为同一类 |

**三种样本形态（均标注 class 0）：**

1. **新鲜白芷根**：黄褐色长圆锥，表面纵皱纹，横向疙瘩丁凸起  
2. **干白芷药材**：灰棕色钝四棱，顶端茎痕同心环纹  
3. **白芷饮片切片**：圆形薄片，断面白色粉性，中间棕色形成层环，密布棕色油点  

### 2.2 标注原则（重要）

- **完整框住**整根白芷或整片饮片，不可只框局部纹理（疙瘩丁、油点、环纹等）  
- 堆叠遮挡时：可见部分可分别标注，或框住最外层轮廓  
- 负样本：画面含白术、独活等易混淆药材时，**不要误标**，可加入背景图增强  
- 格式：YOLO 归一化 `class x_center y_center width height`（0~1）

**标注示例：**

```
# labels/train/baizhi_fresh_001.txt — 新鲜根（细长框）
0 0.512 0.498 0.085 0.620

# labels/train/baizhi_dried_002.txt — 干药材
0 0.445 0.510 0.120 0.580

# labels/train/baizhi_slice_003.txt — 饮片（近圆框）
0 0.500 0.520 0.180 0.175
```

### 2.3 data.yaml

见 `baizhi/dataset/data.yaml`：

```yaml
path: baizhi/dataset
train: images/train
val: images/val
nc: 1
names:
  0: baizhi
```

---

## 三、模型结构：C2f + 坐标注意力 (CA)

在 `ultralytics/nn/modules/` 中新增：

- `CoordinateAttention` — 沿 H/W 方向编码位置信息，强化疙瘩丁、油点等细粒度纹理  
- `C2fCA` — 在 C2f 输出后接入 CA，降低与白术、独活混淆  

模型 YAML：`baizhi/cfg/yolov8s-ca.yaml`（全部 C2f 替换为 C2fCA）

---

## 四、训练参数（针对白芷优化）

| 参数 | 值 | 说明 |
|------|-----|------|
| 预训练 | yolov8s.pt | 精度与 RK3588 速度平衡 |
| imgsz | 640 | 标准输入 |
| epochs | 200 | 小数据集充分收敛 |
| patience | 40 | 早停 |
| optimizer | AdamW | |
| lr0 | 0.0008 | 细粒度特征，较低学习率 |
| cls | 0.3 | 单类检测，降低分类损失权重 |
| mosaic | 1.0 | 开启 |
| copy_paste | 0.3 | 缓解药材堆叠遮挡 |
| mixup | 0.1 | |
| close_mosaic | 15 | 最后 15 epoch 关闭 mosaic |

### 训练命令

```bash
cd ultralytics-main

# 1. 先聚类分析框形（可选，需先有标注）
python baizhi/scripts/anchor_kmeans.py

# 2. 训练
python baizhi/scripts/train.py

# 指定 GPU
python baizhi/scripts/train.py --device 0 --batch 16
```

每轮日志示例：

```
[白芷 Epoch 42/200] Precision=0.9120 | Recall=0.8850 | mAP@0.5=0.9340 | ...
```

---

## 五、锚框 K-means 说明

> **YOLOv8 为 anchor-free**，不使用传统 anchor box。  
> `anchor_kmeans.py` 对标注框宽高做 K-means，用于：
> - 分析白芷细长/圆形框分布  
> - 生成 `shape_priors.yaml` 训练建议  
> - 若迁移 YOLOv5，可直接使用输出的 anchors  

```bash
python baizhi/scripts/anchor_kmeans.py --k 9 --imgsz 640
```

---

## 六、推理代码

### 单张图片

```bash
python baizhi/scripts/detect_image.py --source path/to/image.jpg
python baizhi/scripts/detect_image.py --source baizhi/dataset/images/val --weights baizhi/runs/detect/baizhi_yolov8s_ca/weights/best.pt
```

### 摄像头实时

```bash
python baizhi/scripts/detect_camera.py --camera 0
```

检测框显示中文标签 **「白芷 0.92」**（Pillow 渲染，Windows 使用微软雅黑）。

---

## 七、RKNN 导出流程（RK3588）

### 7.1 PC 端环境

```bash
# 导出环境（x86 Linux / WSL / Docker 推荐）
pip install ultralytics onnx onnxsim
pip install rknn-toolkit2>=2.3.2
pip install "onnx<1.19.0"
```

### 7.2 导出步骤

```bash
# 一键 ONNX + RKNN INT8
python baizhi/scripts/export_rknn.py \
  --weights baizhi/runs/detect/baizhi_yolov8s_ca/weights/best.pt \
  --data baizhi/dataset/data.yaml \
  --imgsz 640 \
  --int8
```

**流程：**

1. `best.pt` → ONNX (opset=12, simplify=True)  
2. ONNX → RKNN (target_platform=rk3588, INT8 量化)  
3. 校准集自动从 `data.yaml` 采样（需含三种形态样本）  
4. 输出 `*_rknn_model/` 目录  

### 7.3 RK3588 板端部署

```bash
# 板端
pip install rknnlite2 opencv-python-headless

python baizhi/scripts/rk3588_infer.py \
  --rknn baizhi/weights/rknn/best-rk3588.rknn \
  --source test.jpg
```

**或使用 Ultralytics 内置 RKNN 后端：**

```python
from ultralytics import YOLO
model = YOLO("baizhi/weights/rknn/best-rk3588.rknn")
model.predict("test.jpg")
```

### 7.4 RK3588 性能参考

| 模型 | 量化 | imgsz | 预估 FPS (RK3588 NPU) |
|------|------|-------|----------------------|
| YOLOv8s-CA | INT8 | 640 | ~25-35 |
| YOLOv8s-CA | FP16 | 640 | ~15-20 |

> C2fCA 较标准 YOLOv8s 略增算力，若 FPS 不足可减小 imgsz=512 或蒸馏到 yolov8n-ca。

---

## 八、训练调优避坑清单

### 数据标注

- [ ] 三种形态（新鲜根/干药材/饮片）**比例均衡**，避免模型只认一种  
- [ ] 框选**整根/整片**，不要框局部疙瘩丁或油点  
- [ ] 加入**白术、独活、当归**等易混淆药材作为负样本（无标注框）  
- [ ] 训练/验证集按形态分层抽样，防止数据泄漏  

### 训练

- [ ] 先跑 `anchor_kmeans.py` 确认宽高比分布  
- [ ] 小数据集（<500 张）适当增大 `epochs`，观察过拟合  
- [ ] `copy_paste=0.3` 对堆叠药材有效，过高会导致伪影  
- [ ] 最后 15 epoch 关闭 mosaic（`close_mosaic=15`）稳定 mAP  
- [ ] 单类检测 `cls=0.3` 即可，不必设为 0  

### 混淆药材

- [ ] 采集与白术（断面有油点但形态不同）、独活（根头有多数支根）对比样本  
- [ ] CA 模块强化纵皱纹+疙瘩丁方向特征，需保证标注框包含这些区域  

### RK3588 部署

- [ ] INT8 校准集必须覆盖三种形态 + 不同光照  
- [ ] ONNX opset 不超过 19  
- [ ] 导出 `batch=1`，动态 batch 板端不支持  
- [ ] 板端后处理需对齐训练 imgsz 与 conf/iou 阈值  
- [ ] Windows 上 rknn-toolkit2 支持有限，建议 WSL2/Docker 导出  

### 常见错误

| 现象 | 原因 | 解决 |
|------|------|------|
| mAP 低、Recall 低 | 只框局部纹理 | 重新标注整根/整片 |
| 误检白术/独活 | 负样本不足 | 增加混淆药材背景图 |
| 训练 NaN | lr 过大 | 降低 lr0 至 5e-4 |
| RKNN 导出失败 | onnx 版本过高 | `pip install "onnx<1.19.0"` |
| 中文标签乱码 | OpenCV 不支持中文 | 使用 `utils_plot.py` Pillow 渲染 |

---

## 九、快速开始 Checklist

```bash
# 0. 安装依赖
pip install ultralytics opencv-python pillow pyyaml

# 1. 放入数据
#    baizhi/dataset/images/train/*.jpg
#    baizhi/dataset/labels/train/*.txt

# 2. K-means 分析（可选）
python baizhi/scripts/anchor_kmeans.py

# 3. 训练
python baizhi/scripts/train.py --device 0

# 4. 推理验证
python baizhi/scripts/detect_image.py --source baizhi/dataset/images/val

# 5. 导出 RKNN
python baizhi/scripts/export_rknn.py --int8
```

---

## 十、核心代码修改说明

本工程对 Ultralytics 源码做了以下扩展（已集成到仓库）：

| 文件 | 修改 |
|------|------|
| `ultralytics/nn/modules/conv.py` | 新增 `CoordinateAttention` |
| `ultralytics/nn/modules/block.py` | 新增 `C2fCA` |
| `ultralytics/nn/tasks.py` | 注册 `C2fCA` 模块 |

如需回退为标准 YOLOv8s，将 `yolov8s-ca.yaml` 中 `C2fCA` 改回 `C2f` 即可。
