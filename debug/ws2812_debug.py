import pigpio
import time

# ================= 配置 =================
LED_GPIO = 19    # BCM编号引脚
LED_COUNT = 96    # LED数量

# WS2812 bit 时序（微秒），按比例放大保证稳定
# SCALE = 2.5  # 放大倍数，让微秒级至少 >=1µs
SCALE = 3  # 放大倍数，让微秒级至少 >=1µs
T0H = int(0.25 * SCALE)  # 0-bit 高电平
T0L = int(1  * SCALE)  # 0-bit 低电平
T1H = int(1  * SCALE)  # 1-bit 高电平
T1L = int(0.25 * SCALE)  # 1-bit 低电平
RESET = 300

# ================= 初始化 pigpio =================
pi = pigpio.pi()
if not pi.connected:
    raise SystemExit("pigpio daemon not running. Use: sudo pigpiod")

pi.set_mode(LED_GPIO, pigpio.OUTPUT)

# ================= 辅助函数 =================
def color_to_grb_bytes(r, g, b):
    """将 RGB 转为 GRB 顺序 WS2812 字节"""
    return [g, r, b]

def ws2812_write(colors):
    """
    colors: [(r,g,b), ...]
    """
    pulses = []
    pi.wave_clear()

    for r, g, b in colors:
        for byte in color_to_grb_bytes(r, g, b):
            for i in range(8):
                if byte & (1 << (7-i)):
                    # 1-bit
                    pulses.append(pigpio.pulse(1<<LED_GPIO, 0, T1H))
                    pulses.append(pigpio.pulse(0, 1<<LED_GPIO, T1L))
                else:
                    # 0-bit
                    pulses.append(pigpio.pulse(1<<LED_GPIO, 0, T0H))
                    pulses.append(pigpio.pulse(0, 1<<LED_GPIO, T0L))

    # RESET 脉冲
    pulses.append(pigpio.pulse(0, 1<<LED_GPIO, RESET))

    pi.wave_add_generic(pulses)
    wid = pi.wave_create()
    if wid >= 0:
        pi.wave_send_once(wid)
        while pi.wave_tx_busy():
            time.sleep(0.001)
        pi.wave_delete(wid)

# ================= 彩虹测试 =================
def rainbow_cycle(num=LED_COUNT, wait=0.03):
    """循环彩虹效果"""
    colors = [
        (20, 0, 0),
        (0, 20, 0),
        (0, 0, 20),
        (0, 0, 0),
        (20, 20, 20),
    ]
    for i in range(len(colors)):
        ws2812_write([colors[(i+j)%len(colors)] for j in range(num)])
        time.sleep(wait)

# ================= 主程序 =================
try:
    print("Starting rainbow cycle. Press Ctrl+C to stop.")
    while True:
        rainbow_cycle(LED_COUNT, 0.0003)
except KeyboardInterrupt:
    print("Stopping, turning off LEDs...")
    ws2812_write([(1,1,1)]*LED_COUNT)
    time.sleep(0.5)
    # ws2812_write([(0,0,0)]*LED_COUNT)
    # time.sleep(0.5)
    pi.stop()
