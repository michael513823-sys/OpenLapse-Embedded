# OpenLapse Embedded (Raspberry Pi Zero 2 W)

## English

### Overview
- Python-based embedded controller for a low-cost, in-incubator time-lapse imaging platform. Provides camera capture/streaming, stepper-driven XYZ motion, LED illumination, and TCP control for a PC-side GUI.

### Core Functions
- Camera capture and MJPEG streaming via `picamera2` / `ffmpeg`.
- Stepper motion on X/Y/Z using TMC2209 over UART + GPIO pulses, homing by stallguard feedback.
- Programmable LED array control with plate-aware addressing (96/24/12/6-well mappings) and status glyphs/progress.
- Time-lapse and focus sweeps executed from PC commands.
- TCP control channel with UDP discovery/heartbeat for headless operation inside incubators.

### Hardware
- Raspberry Pi Zero 2 W (Raspberry Pi OS Lite recommended, no desktop).
- Pi camera module (CSI) with `libcamera`/`picamera2` enabled.
- Three stepper motors (X/Y/Z) + TMC2209 drivers (UART, 115200 baud) and stallguard-based homing.
- Custom controller board for motor drivers and an addressable LED array board (WS2812).
- Stable 5V power, cabling for UART/GPIO; incubator-compatible mounting.

#### GPIO & UART Map (default)
- UART TX/RX: GPIO14/15 (`/dev/serial0`, 115200).
- Motors: X(dir/puls/en)=24/23/13, Y=22/27/6, Z=17/18/5 (BCM).
- LED data: GPIO19.
- See `config.py` for full pin/driver parameters and motion spans.

### Software Setup
1) Raspberry Pi OS Lite, enable **Camera** and **Serial** (disable login shell on UART) via `raspi-config`.
2) Update base system:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```
3) Install dependencies (apt-based):
   ```bash
   sudo apt install -y python3-picamera2 python3-opencv python3-numpy python3-serial python3-rpi.gpio ffmpeg
   ```
   If `picamera2` via apt is unavailable, use Raspberry Pi Imager (Bullseye/Bookworm) or build per Raspberry Pi docs.
4) Clone repo and optional extras:
   ```bash
   git clone <your-fork-url> raspi-openlapse
   cd raspi-openlapse
   python3 -m pip install --upgrade pip
   # Optional: python3 -m pip install opencv-python numpy pyserial
   ```

### Run
- Headless start:
  ```bash
  cd raspi-openlapse
  python3 app.py
  ```
- Pi broadcasts status over UDP (default 64565) and accepts TCP control on the announced port; the PC GUI should auto-discover and connect.
- LED status codes show boot stages (e.g., `ld` load, `NE` network, `CN` connected) and a progress bar.

### Architecture
```
PC GUI ↔ TCP (JSON commands) ↔ libs.connector.PCConnector ↔ app.py command loop
                                    ├─ Motor: libs.motor.MotorController → drivers.tmc2209 (UART+GPIO)
                                    ├─ Light: libs.light.Light → drivers.ws2812
                                    └─ Camera: libs.cam_ffm.MJPEGStreamController (Picamera2 → MJPEG)
UDP broadcast/heartbeat (libs.connector.UDPBroadcast) announces IP/port/status
```
- Commands in `app.py`: `MOVE`, `HOME`, `MOVETO`, `FOCUS`, `LIGHT`. Positions are software-tracked with limits (X≤120000, Y≤56000, Z≤58000 steps by default).
- Homing uses stallguard (no limit switches); `move_to_start()` drives until stall, then zeros position.
- Light layer supports whole-plate, well-specific addressing, glyph display, and progress bar rendering.

### Typical Workflow
1) Power on Pi in incubator and join network (Wi-Fi/Ethernet).
2) Start `app.py`; wait for UDP broadcast; connect via PC GUI.
3) In GUI:
   - `HOME` axes (XY or Z).
   - `MOVETO` / `MOVE` for positioning; `FOCUS` for Z sweep.
   - Configure illumination (`LIGHT`) and start acquisition/streaming.
4) Capture stills via `libs/cam.py` or stream via `libs/cam_ffm.py` MJPEG server (`0.0.0.0:8081` when enabled).

### Configuration
- Motion limits/current/microsteps/homing sensitivity: adjust `config.py` and `MotorController` defaults in `libs/motor.py`.
- Camera resolution/FPS/overlay: tune `MJPEGStreamController` in `libs/cam_ffm.py` or the ffmpeg pipeline in `libs/cam.py`.
- LED brightness/color correction: defaults in `libs/light.py`.
- Network behavior: UDP interval/ports and TCP reconnect delay in `libs/connector.py`.

### Safety & Reliability
- Stallguard homing only; verify mechanical end-stops/soft limits before long moves.
- Ensure driver cooling inside incubator; set motor currents (`set_current`) to avoid overheating.
- Prefer wired Ethernet for long time-lapse; Wi-Fi drops pause command handling until reconnect.

### Troubleshooting
- No camera image: verify `libcamera-hello`, ribbon cable, `picamera2` install.
- UART/TMC no response: disable serial login shell; check TX/RX wiring and addresses (0x00/0x01/0x02).
- LEDs off: check GPIO19 wiring and 5V; try `Light().all()` in Python.
- PC cannot find Pi: allow UDP 64565 on LAN; use `hostname -I` and connect manually to the printed TCP port.

### Contributing
- Please keep changes reproducible and document any new calibration or configuration steps.

---

## 中文

### 项目简介
- 面向培养箱内的低成本时间序列成像平台的树莓派控制端，提供摄像采集/推流、步进电机XYZ运动、LED照明，以及与上位机的网络控制通信。

### 核心功能
- 基于 `picamera2`/`ffmpeg` 的摄像头采集与 MJPEG 推流。
- 通过 UART+GPIO 驱动 TMC2209 控制 X/Y/Z 步进电机，使用 stallguard 归零。
- 可编程 LED 阵列，支持 96/24/12/6 孔板映射、字符显示与进度条。
- 从上位机命令执行时间序列采集与对焦扫描。
- UDP 广播/心跳 + TCP 控制，适合无头运行。

### 硬件需求
- Raspberry Pi Zero 2 W（推荐 Raspberry Pi OS Lite，无桌面）。
- CSI 摄像头，启用 `libcamera`/`picamera2`。
- 三个步进电机（X/Y/Z）+ TMC2209 驱动（UART 115200，stallguard 归零）。
- 电机控制板与 WS2812 LED 阵列板。
- 稳定 5V 供电，UART/GPIO 线束，适配培养箱安装。

#### 默认引脚
- UART TX/RX: GPIO14/15（`/dev/serial0`, 115200）。
- 电机：X(dir/puls/en)=24/23/13，Y=22/27/6，Z=17/18/5（BCM）。
- LED 数据：GPIO19。
- 详见 `config.py` 获取完整参数与行程。

### 软件环境
1) Raspberry Pi OS Lite，`raspi-config` 启用 Camera 和 Serial（关闭 UART 登录）。
2) 更新系统：
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```
3) 安装依赖（apt）：
   ```bash
   sudo apt install -y python3-picamera2 python3-opencv python3-numpy python3-serial python3-rpi.gpio ffmpeg
   ```
   若无 `picamera2` 包，使用官方镜像或按 Raspberry Pi 文档构建。
4) 克隆代码并按需安装额外依赖：
   ```bash
   git clone <your-fork-url> raspi-openlapse
   cd raspi-openlapse
   python3 -m pip install --upgrade pip
   # 可选: python3 -m pip install opencv-python numpy pyserial
   ```

### 运行
- 无头启动：
  ```bash
  cd raspi-openlapse
  python3 app.py
  ```
- 树莓派通过 UDP(默认64565) 广播状态并公布 TCP 端口；上位机 GUI 可自动发现并连接。
- LED 会显示启动阶段字母与进度条（如 `ld` 载入、`NE` 网络、`CN` 连接）。

### 系统架构
```
PC GUI ↔ TCP(JSON 命令) ↔ libs.connector.PCConnector ↔ app.py 循环
                                    ├─ 电机: libs.motor.MotorController → drivers.tmc2209
                                    ├─ 灯板: libs.light.Light → drivers.ws2812
                                    └─ 相机: libs.cam_ffm.MJPEGStreamController
UDP 广播/心跳 (libs.connector.UDPBroadcast) 公布 IP/端口/状态
```
- `app.py` 支持的指令：`MOVE`、`HOME`、`MOVETO`、`FOCUS`、`LIGHT`。位置在软件端维护，并限制行程（默认 X≤120000，Y≤56000，Z≤58000 步）。
- 归零使用 stallguard 无限位检测；`move_to_start()` 检测堵转后置零。
- 灯板支持整板/孔位/字符/进度条显示。

### 典型流程
1) 上电并连接网络。
2) 运行 `app.py`，等待 UDP 广播后由上位机 GUI 连接。
3) 在 GUI 中：
   - 先 `HOME`（XY 或 Z）。
   - 用 `MOVETO` / `MOVE` 定位，用 `FOCUS` 做 Z 扫描。
   - 设置光照 (`LIGHT`)，启动采集/推流。
4) 可用 `libs/cam.py` 拍照，或用 `libs/cam_ffm.py` 启动 MJPEG 推流（默认 `0.0.0.0:8081`）。

### 配置
- 行程、电流、细分、归零灵敏度：修改 `config.py` 与 `libs/motor.py` 默认值。
- 相机分辨率/FPS/叠加：调整 `libs/cam_ffm.py` 或 `libs/cam.py` 中的 ffmpeg 管线。
- LED 亮度与色彩校正：见 `libs/light.py`。
- 网络行为：UDP 周期/端口、TCP 重连等待在 `libs/connector.py`。

### 安全与稳定
- 仅靠 stallguard 归零；长行程前务必确认机械限位或软限位。
- 培养箱内注意驱动散热；合理设置电流 (`set_current`) 避免过热。
- 长时间采集尽量使用有线网络；Wi-Fi 断链会暂停控制直至重连。

### 常见问题
- 无图像：检查 `libcamera-hello`、排线、`picamera2` 安装。
- UART/TMC 无响应：关闭 UART 登录，检查 TX/RX 线序与地址 (0x00/0x01/0x02)。
- 灯不亮：检查 GPIO19 与 5V 供电，Python 中运行 `Light().all()` 测试。
- 上位机找不到：确认 UDP 64565 未被阻断，可用 `hostname -I` 查看 IP，手动连启动日志中的 TCP 端口。

### 贡献
- 欢迎 Issue/PR，分享机械、光路或采集协议改进；请记录可复现的校准与配置步骤。
