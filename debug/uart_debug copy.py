import RPi.GPIO as GPIO
import time
import serial

# ========== BCM 引脚编号 ==========
PITX  = 14
PIRX  = 15
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

# ========== GPIO 初始化 ==========
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in [X_DIR, X_PULS, X_EN,
            Y_DIR, Y_PULS, Y_EN,
            Z_DIR, Z_PULS, Z_EN,
            LIGHT]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# ========== 串口初始化 (TMC2209 UART) ==========
uart = serial.Serial(
    port="/dev/serial0",  # Zero W 默认 UART
    baudrate=115200,
    timeout=0.5
)

# ========== Step2: UART 写读测试 ==========
def calc_crc(dat):
    def reverse_byte(b):
        r = 0
        for i in range(8):
            r = (r << 1) | (b & 1)
            b >>= 1
        return r

    crc = 0
    for b in dat:
        b_rev = reverse_byte(b)  # REFIN: 输入反转
        crc ^= b_rev
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc   # REFOUT 关闭：直接返回


frame = [0x05, 0x02, 0x12]  # 示例数据
crc = calc_crc(frame)
frame.append(crc)
print("发送:", [hex(x) for x in frame])
uart.write(bytearray(frame))

resp = uart.read(16)
print("响应:", resp)

# ========== Step3: 驱动电机测试 ==========
print("\n=== 驱动电机测试 ===")
GPIO.output(X_EN, GPIO.LOW)   # 低电平使能
GPIO.output(X_DIR, GPIO.HIGH) # 设置方向

for i in range(200):  # 200步
    GPIO.output(X_PULS, GPIO.HIGH)
    time.sleep(0.0005)
    GPIO.output(X_PULS, GPIO.LOW)
    time.sleep(0.0005)

GPIO.output(X_EN, GPIO.HIGH)  # 高电平关闭
print("测试完成")

GPIO.cleanup()
