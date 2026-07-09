# elf2 / RK3588 移植说明

## 1. 交叉编译

在宿主机上执行：

```bash
cd /path/to/untitled_1
export SDK_DIR=/path/to/aarch64-buildroot-linux-gnu_sdk-buildroot
bash scripts/build_cross_aarch64.sh
```

如使用自定义工具链，请额外设置：

```bash
export TOOLCHAIN_PREFIX=/path/to/aarch64-linux-gnu-
export QMAKE_BIN=/path/to/qmake
export OPENCV_ROOT=/path/to/sysroot/usr
```

## 2. 部署到板端

把生成的可执行文件和脚本复制到板端：

```bash
scp build-aarch64/drug_recognition root@<elf2>:/tmp/
scp scripts/deepseek_infer.sh scripts/object_recognize.py root@<elf2>:/tmp/
```

然后在板端执行：

```bash
bash /tmp/deepseek_infer.sh --image /tmp/test.jpg --mode object
```

## 3. 板端运行依赖

建议安装：

```bash
sudo apt-get update
sudo apt-get install -y libqt5widgets5 libqt5gui5 libqt5core5a libopencv-core4 libopencv-imgproc4 libopencv-videoio4 libopencv-imgcodecs4 python3 python3-opencv
```

## 4. 运行

```bash
/opt/drug_recognition/drug_recognition
```

## 5. 功能说明

当前工程已支持：

- Qt UI 启动
- USB 摄像头 / V4L2 采集
- 图像抓拍与识别流程
- 识别脚本调用

当前识别脚本是演示版本，若要真正落地到产品环境，需要把 [scripts/deepseek_infer.sh](deepseek_infer.sh) 与 [scripts/object_recognize.py](object_recognize.py) 替换成真实的 RK3588 推理模型或服务调用。