import RPi.GPIO as GPIO
import time
#from ..libs.tool import log

# ========== GPIO 初始化 ==========
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# ========== 引脚定义 ==========
X_DIR = 24
X_PULS = 23
Y_DIR = 22
Y_PULS = 27
Z_DIR = 17
Z_PULS = 18
X_EN = 13
Y_EN = 6
Z_EN = 5

# ========== 引脚初始化 ==========
for pin in [X_DIR, Y_DIR, Z_DIR,
            X_EN, Y_EN, Z_EN]:
    GPIO.setup(pin, GPIO.OUT)

# 默认状态
GPIO.output([X_DIR, Y_DIR, Z_DIR], GPIO.LOW)
GPIO.output([X_EN, Y_EN, Z_EN], GPIO.HIGH)  # 高电平关闭使能

# 使用PWM控制PULS引脚
for pin in [X_PULS, Y_PULS, Z_PULS]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)
    GPIO.PWM(pin, 1000).start(0)  # 初始频率1kHz，占空比0


# ========== 步进电机驱动类 ==========
class Stepper:
    def __init__(self, dir_pin, puls_pin, en_pin):
        self.dir_pin = dir_pin
        self.puls_pin = puls_pin
        self.en_pin = en_pin
        GPIO.output(self.dir_pin, GPIO.LOW)
        GPIO.output(self.puls_pin, GPIO.LOW)
        GPIO.output(self.en_pin, GPIO.LOW)  # 低电平使能

    def move_steps(self, t, direction=1, freq=2000):
        """
        控制步进电机运动
        """
        GPIO.output(self.dir_pin, GPIO.HIGH if direction else GPIO.LOW)

        pwm = GPIO.PWM(self.puls_pin, freq)
        pwm.start(50)  # 占空比50%
        time.sleep(t)  # 秒
        pwm.stop()

    def enable(self):
        GPIO.output(self.en_pin, GPIO.LOW)  # 低电平使能
        
    def disable(self):
        GPIO.output(self.en_pin, GPIO.HIGH)  # 高电平关闭使能


if __name__ == "__main__":
    # 创建三个轴对象
    x_axis = Stepper(X_DIR, X_PULS, X_EN)
    y_axis = Stepper(Y_DIR, Y_PULS, Y_EN)
    z_axis = Stepper(Z_DIR, Z_PULS, Z_EN)

    # 使能电机
    

    while True:
        cmd = input("输入命令 (x/y/z: 测试X/Y/Z轴, q: 退出): ").strip().lower()
        if cmd == 'q':
            break
        elif cmd == 'x':
            freq = input("输入速度 (频率): ").strip()
            x_axis.enable()
            x_axis.move_steps(5, direction=1, freq=int(freq))
            time.sleep(0.5)
            x_axis.move_steps(5, direction=0, freq=int(freq))
            x_axis.disable()
        elif cmd == 'y':
            freq = input("输入速度 (频率): ").strip()
            y_axis.enable()
            y_axis.move_steps(5, direction=1, freq=int(freq))
            time.sleep(0.5)
            y_axis.move_steps(5, direction=0, freq=int(freq))
            y_axis.disable()
        elif cmd == 'z':
            freq = input("输入速度 (频率): ").strip()
            z_axis.enable()
            z_axis.move_steps(5, direction=1, freq=int(freq))
            time.sleep(0.5)
            z_axis.move_steps(5, direction=0, freq=int(freq))
            z_axis.disable()
        else:
            #log("未知命令")
            print("未知命令")

    

    GPIO.cleanup()
