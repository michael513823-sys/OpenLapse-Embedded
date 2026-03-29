# ------------ 基本配置 ------------- #
# 模式选择
DEFAULT_MODE = 0  #

# ------------ GPIO配置 ------------- #
# BCM编号
PITX=14
PIRX=15
X_DIR = 24
X_PULS = 23
Y_DIR = 22
Y_PULS = 27
Z_DIR = 17
Z_PULS = 18
X_EN = 13
Y_EN = 6
Z_EN = 5
LIGHT = 19

# 摇杆引脚, ADS1220 *3
ADS1220_SCK_PIN = 18
ADS1220_MISO_PIN = 19 # ADC_DOUT
ADS1220_MOSI_PIN = 13  # ADC_DIN
ADS1220_CS1_PIN = 17   # ADC1_CS
ADS1220_CS2_PIN = 16   # ADC2_CS
ADS1220_CS3_PIN = 4   # ADC3_CS
ADS1220_DRDY1_PIN = 34  # ADC1_DRDY
ADS1220_DRDY2_PIN = 35  # ADC2_DRDY
ADS1220_DRDY3_PIN = 32  # ADC3_DRDY

# 调速旋钮
SPEED_PIN = 36  # ESP32_ADC (SENSOR_VP)

# 按键
KEY_PIN = 13  # ESP32_ADC (SENSOR_VN)


# ------------ UART地址, TMC2209 ------------- #
UART_X_ADDR = 0x00
UART_Y_ADDR = 0x01
UART_Z_ADDR = 0x02

# ------------ UART波特率，TMC2209 ------------- #
UART_BAUDRATE = 115200

# ------------ 电机默认方向 ------------- #
X_INIT_DIR = 0
Y_INIT_DIR = 0
Z_INIT_DIR = 0

# ------------ 无限位回中参数设置，TMC2209 ------------- #
RETURN_TO_ZERO_SPEED_FAST = 4000  # 回中速度
RETURN_TO_ZERO_SPEED_SLOW = 1000  # 回中速度
RETURN_TO_ZERO_MERS = 16  # 回中细分
RETURN_TO_ZERO_SGTHRS = 100  # 回中灵敏度
RETURN_TO_ZERO_DROP = 60  # SG下降多少认为堵转
RETURN_TO_ZERO_EN_SpreadCycle = False  # 是否使用SpreadCycle模式


# ------------ 操作设置 ------------- #
X_SPEED_COEF = 1.0
Y_SPEED_COEF = 1.0
Z_SPEED_COEF = 1.0


# ------------ 摇杆ADC配置 ------------- #
JOYSTICK_ADC_FULLSCALE = (1<<24)  # 24位ADC满量程
JOYSTICK_CENTER_THRESHOLD = 0.15 * JOYSTICK_ADC_FULLSCALE  # 中心点阈值


# ------------ STEP_RMT ------------- #
RMT_CLK_DIV = 40  # RMT时钟分频，影响最小脉冲宽度，时钟频率为 80MHz/(分频数) ，最小脉冲宽度为1/时钟频率
RMT_CHUNK_SIZE = 4000  # 每次发送的最大步数，避免阻塞后台线程太久
RMT_MAX_FREQ = 40_000  # 最大频率，避免过快


# ------------ 位置模式 ------------- #
POS_MODE_MERS = 256
POS_MODE_LEAD_SCREW_PITCH = 2  # 丝杆导程，单位mm

POS_MODE_SPAN_XY_MM = 2  # 最大行程，单位mm
POS_MODE_SPAN_Z_MM = 0.5  # 最大行程，单位mm

EN_DEGE_STEP = False  # 是否使用双边沿步进，TMC2209支持，速度更快

POS_TOTAL_STEPS_XY = int(POS_MODE_MERS * 200 * POS_MODE_SPAN_XY_MM / POS_MODE_LEAD_SCREW_PITCH)
POS_TOTAL_STEPS_Z = int(POS_MODE_MERS * 200 * POS_MODE_SPAN_Z_MM / POS_MODE_LEAD_SCREW_PITCH)

POS_MODE_IRUN_XY   = 25  # 运行电流
POS_MODE_IRUN_Z = 25  # Z轴运行电流
POS_MODE_IHOLD_XY  = 10  # 保持电流
POS_MODE_IHOLD_Z = 10   # Z轴保持电流



MAPPER_RAW_MIN_X = -1 * (1<<23)  # 校准摇杆最小值, 24位ADC，相对于中心减去-(1<<23)
MAPPER_RAW_MAX_X = 1 * (1<<23)   # 校准摇杆最大值, 24位ADC
MAPPER_RAW_MIN_Y = -1 * (1<<23)  # 校准摇杆最小值, 24位ADC，相对于中心减去-(1<<23)
MAPPER_RAW_MAX_Y = 1 * (1<<23)   # 校准摇杆最大值, 24位ADC
MAPPER_RAW_MIN_Z = -1 * (1<<23)  # 校准摇杆最小值, 24位ADC，相对于中心减去-(1<<23)
MAPPER_RAW_MAX_Z = 1 * (1<<23)   # 校准摇杆最大值, 24位ADC

MAPPER_DEADZONE_XY = 0.002  # 摇杆死区比例
MAPPER_DEADZONE_Z = 0.002  # 摇杆死区比例

MAPPER_HYSTERESIS_XY = 0.8  # 摇杆迟滞比例
MAPPER_HYSTERESIS_Z = 0.8  # 摇杆迟滞比例

MAPPER_EMA_ALPHA_XY = 512  # 摇杆指数平滑系数
MAPPER_EMA_ALPHA_Z = 512  # 摇杆指数平滑系数

MAPPER_QUANT_STEPS_XY = 1  # 摇杆量化步数
MAPPER_QUANT_STEPS_Z = 1  # 摇杆量化步数

MAPPER_MAX_STEP_DELTA_PER_TICK_XY = POS_TOTAL_STEPS_XY / 10  # 摇杆每次最大步数变化
MAPPER_MAX_STEP_DELTA_PER_TICK_Z = POS_TOTAL_STEPS_Z / 10  # 摇杆每次最大步数变化

POS_CHUNK_SIZE = 4000  # 每次发送的最大步数，避免阻塞后台线程太久
POS_ERR_THRESHOLD = 10  # 误差小于多少步不动

POS_START_MIDDLE = True  # 启动时回中位置在中点
POS_FILTER_NOISE = True  # 启动时滤除抖动
POS_FILTER_METHOD = 'kalman'  # 滤波方法
POS_FILTER_WINDOW_SIZE = 10  # 滤波窗口大小 # mean or median使用
POS_FILTER_LP_ALPHA = 0.1  # 滤波指数平滑系数,low_pass使用
POS_FILTER_KF_Q = 8  # 卡尔曼滤波Q值
POS_FILTER_KF_R = 10000   # 卡尔曼滤波R值

POS_MAX_FREQ = 35_000  # 最大频率，避免过快

POS_SLEEP_DELAY_MS = 1  # 主循环延时，单位毫秒
