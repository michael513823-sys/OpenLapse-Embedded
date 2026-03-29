# 导入GPIO库
import RPi.GPIO as GPIO # type: ignore
import time
import threading

# 添加上级目录到sys.path，以便导入本地模块
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from drivers.tmc2209 import TMC2209
import config
from libs.tool import log




import time
import os
import RPi.GPIO as GPIO  # type: ignore


class MotorController:
    def __init__(self, uart, addr, dir_pin, pulse_pin, enable_pin,
                 speed_coef: float = 1.0, reverse_dir: bool = False,
                 begin_with_reverse: bool = True
                 ):
        # from drivers.tmc2209 import TMC2209  # 延迟导入，防止模块问题

        # --- 驱动IC ---
        self.driver = TMC2209(uart, addr)

        # --- GPIO ---
        self.dir_pin = dir_pin
        self.pulse_pin = pulse_pin
        self.enable_pin = enable_pin

        # --- 控制参数 ---
        self.speed_coef = speed_coef
        self.reverse_dir = reverse_dir
        self.microsteps = 16
        self.double_edge_step = True  # 双边沿触发步进
        self.begin_with_reverse = begin_with_reverse # 归零时，先反向运动一段距离，防止起始位置卡死

        # --- 归零标志 ---
        self.is_homed = False
        self.position = 0  # 当前步数位置

        # 多线程加锁
        self.lock = threading.Lock()

        self.motor_busy = False

        self.is_focusing = False

        # --- 尝试绑定CPU核心（减少调度抖动）---
        try:
            os.sched_setaffinity(0, {2}) # type: ignore
        except Exception:
            pass

        # --- 初始化 ---
        self._init_motor()

    # 初始化电机
    def _init_motor(self):
        self.driver.init_tmc2209(chopconf_mres_limit_check=16)
        if self.driver.init_success:
            log("[TMC2209] Initialized successfully")
        else:
            log("[TMC2209] Initialization failed")

        # --- GPIO模式 ---
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.dir_pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.enable_pin, GPIO.OUT, initial=GPIO.HIGH) # 默认禁能
        self._init_pulse_steps()

        # 默认方向、低电平
        GPIO.output(self.dir_pin, GPIO.HIGH if self.reverse_dir else GPIO.LOW)
        # 默认禁能
        self.enable_motor(False)

    # 初始化pulse引脚
    def _init_pulse_steps(self):
        # 配置pulse引脚
        GPIO.setup(self.pulse_pin, GPIO.OUT, initial=GPIO.LOW)
        # 默认脉冲、低电平
        GPIO.output(self.pulse_pin, GPIO.LOW)

    def _init_pulse_pwm(self):
        # 配置pulse引脚
        GPIO.setup(self.pulse_pin, GPIO.OUT, initial=GPIO.LOW)
        # 配置为PWM模式
        self.pwm = GPIO.PWM(self.pulse_pin, 1000) # 初始频率1kHz
        self.pwm.start(0)  # 初始占空比0%


    # 初始化
    # --- 设置细分 ---
    def set_microsteps(self, microsteps: int):
        if microsteps in [1, 2, 4, 8, 16, 32, 64, 128, 256]:
            self.microsteps = microsteps
            self.driver.set_microstep(microsteps, en_double_edge_step=self.double_edge_step)
        else:
            log("[WARN] Invalid microsteps value")

    # --- 设置电流 ---
    def set_current(self, irun: int = 15, ihold: int = 5, delay: int = 4):
        if 0 < irun <= 31:
            self.driver.set_current(ihold, irun, delay)
        else:
            log("[WARN] Invalid current value")
    # --- SpreadCycle ---
    def en_spreadcycle(self, enable: bool = True):
        if enable:
            self.driver.set_en_SpreadCycle(1)
        else:
            self.driver.set_en_SpreadCycle(0)
    
    # --- 设置方向 ---
    def set_dir(self, direction: int):
        """
        reverse_dir = False,
        direction:
            0:靠近电机运动, dir_pin:LOW
            1:远离电机运动, dir_pin:HIGH
        """
        if direction == 0:
            GPIO.output(self.dir_pin, GPIO.HIGH if self.reverse_dir else GPIO.LOW)
        else:
            GPIO.output(self.dir_pin, GPIO.LOW if self.reverse_dir else GPIO.HIGH)

    # --- 使能控制 ---
    # 使用原则：在操作电机方法内，调用 enable_motor(True)，结束后保持使能状态
    # 由外部调用者负责在适当时机调用 enable_motor(False)
    def enable_motor(self, enable: bool = True):
        GPIO.output(self.enable_pin, GPIO.LOW if enable else GPIO.HIGH)

    # ==================================================
    #                运行指定步数（输出固定脉冲数）
    # ==================================================
    def run_motor_steps(self, steps: int, freq: float, direction: int = 0, timeout: float = 60):
        """
        以指定频率（Hz）输出指定步数的方波脉冲
        可达到 8~10 kHz 稳定输出
        """
        if steps == 0:
            return
        if freq <= 0:
            raise ValueError("Frequency must be positive")
        
        # 计算执行操作时间
        target_time = steps / freq
        if target_time > timeout:
            log(f"[WARN] Target time {target_time:.1f}s is too long, consider reducing steps or increasing frequency.")
            return

        # --- 计算时间 ---
        period_ns = int(1_000_000_000 / freq)
        half_period = period_ns // 2
        total_steps = abs(steps)

        log(f"[RUN] freq={freq:.1f}Hz, steps={total_steps}, period={period_ns/1000:.1f}µs")

        try:
            # 运动忙碌标志
            self.motor_busy = True

            # 设置方向
            self.set_dir(direction)
            # 使能电机
            self.enable_motor(True)
            now_step = 0
            # 开始运动
            while now_step < total_steps:

                t0 = time.perf_counter_ns()

                # 高电平
                GPIO.output(self.pulse_pin, GPIO.HIGH)
                while (time.perf_counter_ns() - t0) < half_period:
                    pass

                # 低电平
                GPIO.output(self.pulse_pin, GPIO.LOW)
                while (time.perf_counter_ns() - t0) < period_ns:
                    pass

                now_step += 1

                # 上锁存位置
                with self.lock:
                    # 记录位置
                    if direction == 0:  # 靠近电机运动
                        self.position -= 1  # 当前位置减1
                    else:
                        self.position += 1

                    if self.position <= 0:
                        self.position = 0
                        break
            
            # 释放忙碌状态
            self.motor_busy = False


        finally:
            # 安全退出
            GPIO.output(self.pulse_pin, GPIO.LOW)
            # self.enable_motor(False)
            log("[DONE] Motor run complete.")
    
    # ==================================================
    #                运行指定频率（PWM模式）
    # ==================================================
    def run_motor_pwm(self, freq: float, duty_cycle: float=50, direction: int = 0):
        """
        以指定频率（Hz）和占空比（%）输出PWM信号
        """
        if not hasattr(self, "pwm"):
            self._init_pulse_pwm()

        if freq <= 0:
            log("Frequency must be positive")
            return
        if not (0 <= duty_cycle <= 100):
            log("Duty cycle must be between 0 and 100")
            return
        # 设置方向
        self.set_dir(direction)
        # 使能电机
        self.enable_motor(True)
        # 启动PWM
        self.pwm.ChangeFrequency(freq)
        self.pwm.start(duty_cycle)

        self.motor_busy = True

    # 停止PWM
    def stop_motor_pwm(self):
        self.pwm.stop()
        self.motor_busy = False

    # ==================================================
    #           运行状态检测（检测电机感生电动势）
    # ==================================================
    def position_detection(self, RETURN_TO_ZERO_SGTHRS, RETURN_TO_ZERO_DROP, debug: bool = False, debuge_time: int = 30):
        """
        检测 TMC2209 的 StallGuard 感生电动势值，判断电机是否触限。
        """
        MAX_SGTHRS = 300   # 感生电动势最大值，超过该值则直接丢弃
        # RETURN_TO_ZERO_SGTHRS = 200   # 感生电动势阈值
        # RETURN_TO_ZERO_DROP = 50      # 感生电动势下降幅度阈值

        sg_result_list = []
        low_sg_result_list = []
        cleaned = False
        drop_count = 0
        sg_result_window_size = 30  # 用于计算平均值的窗口大小
        drop_count_threshold = 10  # 触发停止的下降计数阈值

        if debug:
            log("check SGTHRS (debug mode)...")
            now = time.time()
            while True:
                sg_result = self.driver.read_sg_result()
                if sg_result is not None:
                    sg_result_list.append(sg_result)
                    if len(sg_result_list) % 10 == 0:
                        log(f"sg_result: {sg_result}")
                if time.time() - now > debuge_time:
                    break
                time.sleep(0.002)
            log("check SGTHRS done.")
            return sg_result_list, low_sg_result_list

        # 非调试模式
        log("Detecting position (auto-stop)...")
        start_time = time.time()

        while True:
            sg_result = self.driver.read_sg_result()
            if sg_result is not None:
                if sg_result > MAX_SGTHRS:
                    continue
                # 记录结果
                sg_result_list.append(sg_result)
                log(f"sg_result: {sg_result}")

            # 清理前期不稳定样本（仅一次）
            if not cleaned and len(sg_result_list) >= 18:
                sg_result_list = [sg_result_list[-1]]
                cleaned = True
                log(f"sg_result_list cleaned: {sg_result_list}")

            if cleaned:
                # 足够数据后才进行判断
                if len(sg_result_list) >= sg_result_window_size:
                    window = sg_result_list[-sg_result_window_size:]
                    avg_sg = sum(window) / sg_result_window_size
                    log(f"avg_sg: {avg_sg:.2f}, sg_result_list: {sg_result_list}")

                    # 检测下降趋势
                    if (avg_sg - sg_result > RETURN_TO_ZERO_DROP) or (sg_result < RETURN_TO_ZERO_SGTHRS):
                        # 检测到下降
                        drop_count += 1
                        low_sg_result_list.append(sg_result_list.pop())  # 记录低值，并从主列表移除
                        log(f"Drop detected! drop_count: {drop_count}, low_sg_result_list: {low_sg_result_list}")
                    else:
                        # 未检测到下降，衰减计数
                        drop_count = max(0, drop_count - 1)
                        

                    # 判断触限条件：低值大于 drop_count_threshold
                    if drop_count > drop_count_threshold:
                        break

                    # # 判断触限条件2：最近 drop_count_threshold 次平均值低于阈值
                    # if (drop_count > drop_count_threshold) and (sum(low_sg_result_list[-drop_count_threshold:]) / drop_count_threshold < RETURN_TO_ZERO_SGTHRS):
                    #     break

                # 限制循环频率
                time.sleep(0.001)
        log(f"[STOP] SG下降检测触发 at {time.time() - start_time:.2f}s")
        return sg_result_list, low_sg_result_list

    # ==================================================
    #                无限位归零
    # ==================================================
    # 无限位归零，先负向运动到起始位置
    def move_to_start(self, start_dir: int = 0,sg_drop:int=100,min_sg:int=150,speed:float=1):
        fast_freq = int(10_000 * speed)
        slow_freq = int(1000 * speed)
        RETURN_TO_ZERO_SGTHRS = min_sg   # 感生电动势阈值
        RETURN_TO_ZERO_DROP = sg_drop     # 感生电动势下降幅度
        try:
            if self.driver.init_success:
                # 设置细分、电流
                self.set_microsteps(16)
                self.set_current(irun=30, ihold=15, delay=4)

            log("Moving to start position...1")
            # 移动方向
            # self.set_dir(start_dir)
            # 初始化PWM模式
            self._init_pulse_pwm()

            # 用一个参数来觉得是否先反向运动一段距离，防止起始位置卡死
            if self.begin_with_reverse == True:
                self.run_motor_pwm(fast_freq, direction=int(not start_dir))
                time.sleep(1)
                self.stop_motor_pwm()
                time.sleep(0.5)

            # 开始运动
            self.run_motor_pwm(fast_freq,direction=start_dir)

            # 位置检测(阻塞)
            sg_result_list, low_sg_result_list = self.position_detection(RETURN_TO_ZERO_SGTHRS, RETURN_TO_ZERO_DROP, debug=False)

            # 停止PWM
            self.stop_motor_pwm()
            # 短暂停止
            # time.sleep(0.5)
            
            log("Moving to start position...2")
            # 反向慢速运动
            # self.set_dir(int(not start_dir))
            # 重新启动PWM
            self.run_motor_pwm(slow_freq, direction=int(not start_dir))
            # 持续一定时间
            time.sleep(5)

            log("Moving to start position...3")
            # 再次回零
            self.set_dir(start_dir)
            self.run_motor_pwm(slow_freq, direction=start_dir)
            time.sleep(3)

            # 关闭 PWM
            self.pwm.stop()

            # 切换回软件脉冲模式
            self._init_pulse_steps()

            log(sg_result_list)
            log(low_sg_result_list)

            # 归零完成
            self.is_homed = True
            self.position = 0
            log("Homing complete. Position reset to 0.")

        except Exception as e:
            log(f"Error occurred while moving to start position: {e}")


    # =================================================
    #            移动到指定位置（根据position）
    # =================================================
    def move_to_position(self, target_position: int, freq: float = 2000, auto_home: bool = False):
        """
        移动到指定位置（相对于当前位置的绝对位置）
        """
        if not self.is_homed:
            if auto_home:
                log("Motor not homed yet. Performing auto homing...")
                self.move_to_start()
            else:
                log("[WARN] Motor not homed yet. Please home the motor first or enable auto homing.")
                return
        if target_position < 0:
            log("[WARN] Target position must be non-negative.")
            return

        steps_to_move = target_position - self.position
        if steps_to_move == 0:
            log("[INFO] Already at target position.")
            return

        direction = 1 if steps_to_move > 0 else 0
        steps = abs(steps_to_move)

        log(f"Moving to position {target_position} from {self.position}, steps: {steps}, direction: {direction}")
        self.run_motor_steps(steps, freq, direction=direction)
        log(f"Arrived at position {self.position}")


    # 获取位置
    def get_position(self):
        with self.lock:
            return self.position
        
    # 获取忙碌状态
    def is_busy(self):
        return self.motor_busy




# debug
if __name__ == "__main__":
    
    import serial # type: ignore
    uart = serial.Serial("/dev/serial0", baudrate=115200, timeout=0)

    Z_DIR = 24
    Z_PULS = 23
    Y_DIR = 22
    Y_PULS = 27
    X_DIR = 17
    X_PULS = 18
    Z_EN = 13
    Y_EN = 6
    X_EN = 5

    x_motor = MotorController(uart, 0x02, dir_pin=X_DIR, pulse_pin=X_PULS, enable_pin=X_EN)
    y_motor = MotorController(uart, 0x01, dir_pin=Y_DIR, pulse_pin=Y_PULS, enable_pin=Y_EN,reverse_dir=True)
    z_motor = MotorController(uart, 0x00, dir_pin=Z_DIR, pulse_pin=Z_PULS, enable_pin=Z_EN,reverse_dir=True,begin_with_reverse=False)
    try:
        x_motor.set_microsteps(16)
        y_motor.set_microsteps(16)
        z_motor.set_microsteps(16)

        # 设置电流
        x_motor.set_current(irun=31, ihold=15, delay=4)
        y_motor.set_current(irun=31, ihold=15, delay=4)
        z_motor.set_current(irun=31, ihold=15, delay=4)

        x_motor.enable_motor(True)
        y_motor.enable_motor(True)
        z_motor.enable_motor(True)

        # x_motor.set_dir(0)
        # z_motor.set_dir(0)
        # x_motor.run_motor_steps(20000, 5_000)
        
        time.sleep(1)
        log("运动到指定位置")

        # x_motor.run_motor_steps(5000*5, 5_000, direction=1)
        # z_motor.run_motor_steps(5000*5, 5_000, direction=1)
        log(f"x_motor 当前位置：{x_motor.position}")
        log(f"y_motor 当前位置：{y_motor.position}")
        log(f"z_motor 当前位置：{z_motor.position}")

        time.sleep(1)
        log("开始归零")

        x_motor.move_to_start(sg_drop=100,min_sg=120)
        y_motor.move_to_start(sg_drop=100,min_sg=120)
        z_motor.move_to_start(sg_drop=100,min_sg=120,speed=0.6)

        print(x_motor.position)
        print(y_motor.position)
        print(z_motor.position)


        log("归零完成")
        # 切换到工作模式
        x_motor.set_microsteps(16)
        y_motor.set_microsteps(16)
        z_motor.set_microsteps(256)

        log("移动到指定位置 5000")
        x_motor.move_to_position(50000, freq=6000)
        y_motor.move_to_position(33000, freq=6000)
        z_motor.move_to_position(50000, freq=6000)

        log("移动完成")
        print(x_motor.position)
        print(y_motor.position)
        print(z_motor.position)

    except KeyboardInterrupt:
        log("程序中断，退出")
        print(x_motor.position)
        print(y_motor.position)
        print(z_motor.position)
    finally:
        GPIO.cleanup()
        log("GPIO cleaned up")
