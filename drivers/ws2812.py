import time
from rpi_ws281x import PixelStrip, Color, ws

# ================= 配置 =================
LED_COUNT = 96       # LED 数量
LED_PIN = 19         # DIN引脚，BCM19，必须支持硬件PWM
LED_CHANNEL = 1     # 使用PWM通道1，对应BCM19
BRIGHTNESS = 255     # 亮度
PWM_FREQ = 800000  # PWM频率，通常为800kHz


# 创建类
class WS2812:
    def __init__(self, led_count=LED_COUNT, led_pin=LED_PIN, led_channel=LED_CHANNEL, brightness=BRIGHTNESS, pwm_freq=PWM_FREQ):
        self.led_count = led_count
        self.led_pin = led_pin
        self.led_channel = led_channel
        self.brightness = brightness
        self.pwm_freq = pwm_freq

        # 颜色矫正参数
        self.color_correction = {
            'r': 255,
            'g': 255,
            'b': 255
        }

        # 创建 PixelStrip 对象
        self.strip = PixelStrip(
            self.led_count,
            self.led_pin,
            freq_hz=self.pwm_freq,
            dma=10,     # DMA通道
            invert=False,
            brightness=self.brightness,
            channel=self.led_channel,
            strip_type=ws.WS2811_STRIP_GRB  # 颜色顺序 (GRB)
        )

        # 初始化
        self.strip.begin()

    # 颜色矫正
    def set_color_correction(self, r, g, b):
        """设置颜色矫正参数"""
        self.color_correction['r'] = r
        self.color_correction['g'] = g
        self.color_correction['b'] = b
    
    # 全局亮度
    def set_global_brightness(self, brightness):
        """设置全局亮度"""
        self.brightness = brightness
        self.strip.setBrightness(brightness)

    def set_pixel_color(self, index, r, g, b, brightness=None):
        """设置单个像素颜色"""
        if 0 <= index < self.led_count:
            r = int(r * self.color_correction['r']/255.0)
            g = int(g * self.color_correction['g']/255.0)
            b = int(b * self.color_correction['b']/255.0)
            if brightness is not None:
                r = int(r * brightness/255.0)
                g = int(g * brightness/255.0)
                b = int(b * brightness/255.0)
            self.strip.setPixelColor(index, Color(r, g, b))

    def show(self):
        """更新显示"""
        self.strip.show()

    def clear(self):
        """清除所有像素"""
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()

    # ---- 其他方法 ----
    def fill_all(self, r, g, b, brightness=None):
        """填充所有像素颜色"""
        for i in range(self.led_count):
            self.set_pixel_color(i, r, g, b, brightness)
        self.show()
    
    # 彩虹显示
    def rainbow_cycle(self, brightness=None, wait=0.000001):
        """彩虹循环效果"""
        def wheel(pos):
            """生成彩虹颜色"""
            if pos < 85:
                return 255 - pos*3, pos*3, 0
            elif pos < 170:
                pos -= 85
                return 0, 255 - pos*3, pos*3
            else:
                pos -= 170
                return pos*3, 0, 255 - pos*3

        for j in range(256):
            for i in range(self.led_count):
                idx = (i + j) & 255
                self.set_pixel_color(i, *wheel(idx), brightness=brightness)
            self.show()
            time.sleep(wait)

        

# debug 代码
if __name__ == "__main__":
    led_panel = WS2812()
    led_panel.clear()

    led_panel.set_color_correction(255, 200, 150)  # 设置颜色矫正
    led_panel.set_global_brightness(200)  # 设置全局亮度
    try:
        cmd = input("输入命令 (c: 彩虹循环, a: 逐个亮起, w/r/g/b: 全亮, n(0-95):灯珠序号): ").strip().lower()
        print("Starting rainbow cycle. Press Ctrl+C to stop.")
        if cmd == 'w':
            led_panel.fill_all(255, 255, 255, brightness=20)
        if cmd == 'a':
            while True:
                for n in range(LED_COUNT):
                    led_panel.clear()
                    led_panel.set_pixel_color(n, 255, 255, 255, brightness=50)
                    led_panel.show()
                    time.sleep(0.01)
        
        elif cmd == 'r':
            led_panel.fill_all(255, 0, 0, brightness=20)
        elif cmd == 'g':
            led_panel.fill_all(0, 255, 0, brightness=20)
        elif cmd == 'b':
            led_panel.fill_all(0, 0, 255, brightness=20)

        elif cmd.isdigit() and 0 <= int(cmd) < LED_COUNT:
            n = int(cmd)
            led_panel.clear()
            led_panel.set_pixel_color(n, 255, 255, 255, brightness=50)
            led_panel.show()
        elif cmd == 'c':
            while True:
                led_panel.rainbow_cycle()
        else:
            pass

        # 停在这里
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Stopping, turning off LEDs...")
        led_panel.clear()
