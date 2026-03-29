import time
from rpi_ws281x import PixelStrip, Color, ws

# ================= 配置 =================
LED_COUNT = 96       # LED 数量
LED_PIN = 19         # BCM19
BRIGHTNESS = 255     # 亮度
ORDER = ws.WS2811_STRIP_GRB  # 注意是整数常量

# 创建 PixelStrip 对象
strip = PixelStrip(
    LED_COUNT,
    LED_PIN,
    freq_hz=800000,
    dma=10,
    invert=False,
    brightness=20,
    channel=1,           # 必须指定 channel=1
    strip_type=ws.WS2811_STRIP_GRB
)
strip.begin()



# 彩虹函数
def wheel(pos):
    if pos < 85:
        return Color(255 - pos*3, pos*3, 0)
    elif pos < 170:
        pos -= 85
        return Color(0, 255 - pos*3, pos*3)
    else:
        pos -= 170
        return Color(pos*3, 0, 255 - pos*3)

def rainbow_cycle(wait=0.000002):
    for j in range(256):
        for i in range(LED_COUNT):
            idx = (i + j) & 255
            strip.setPixelColor(i, wheel(idx))
        strip.show()
        time.sleep(wait)

# 白色全亮
def white_full():
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(255,255,255))
    strip.show()

# 红色全亮
def red_full():
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(255,0,0))
    strip.show()

# 绿灯全亮
def green_full():
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0,255,0))
    strip.show()

# 蓝灯全亮
def blue_full():
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0,0,255))
    strip.show()

# 主程序
try:
    cmd = input("输入命令 (r: 彩虹循环, w/r/g/b: 白/红/绿/蓝全亮, q: 退出): ").strip().lower()
    print("Starting rainbow cycle. Press Ctrl+C to stop.")
    while True:
        if cmd == 'q':
            break
        elif cmd == 'w':
            white_full()
        elif cmd == 'r':
            red_full()
        elif cmd == 'g':
            green_full()
        elif cmd == 'b':
            blue_full()
        else:
            rainbow_cycle()
except KeyboardInterrupt:
    print("Stopping, turning off LEDs...")
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0,0,0))
    strip.show()
