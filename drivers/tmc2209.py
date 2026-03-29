# 树莓派Zero W控制TMC2209步进电机驱动芯片
# 使用UART单总线通信，波特率115200

# 导入GPIO库
import RPi.GPIO as GPIO
import time

# 添加上级目录到sys.path，以便导入本地模块
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))


# from libs.tool import log
import config

def log(msg,*args, **kwargs):
    print(msg, *args, **kwargs)

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

# 定义一个uart


class TMC2209:
    def __init__(self, uart, addr):
        self.uart = uart
        self.addr = addr
        self.init_success = False

        self.microsteps_tab = {
            256: 0b0000,
            128: 0b0001,
            64: 0b0010,
            32: 0b0011,
            16: 0b0100,
            8: 0b0101,
            4: 0b0110,
            2: 0b0111,
            1: 0b1000
        }

    # TMC2209的CRC8校验，需要反转
    def calc_crc(self, dat):
        try:
            # 反转字节
            def reverse_byte(b):
                r = 0
                for i in range(8):
                    r = (r << 1) | (b & 1)
                    b >>= 1
                return r
            
            crc = 0
            for b in dat:
                b_rev = reverse_byte(b)   # REFIN
                crc ^= b_rev
                for _ in range(8):
                    if crc & 0x80:
                        crc = ((crc << 1) ^ 0x07) & 0xFF
                    else:
                        crc = (crc << 1) & 0xFF
            return crc   # REFOUT=0
        except Exception as e:
            log("Fail to calculate CRC:", e)
            return None

    # 读取寄存器（丢弃单总线回显）
    def read_register(self, reg):
        try:
            sync = 0x05
            reg_addr = reg & 0x7F  # 读操作 bit7=0
            dat = [sync, self.addr, reg_addr]
            dat.append(self.calc_crc(dat))
            self.uart.write(bytearray(dat))
            # log("uart.write", dat)

            time.sleep(0.01)
            resp = self.uart.read(16)
            if not resp or len(resp) < 8:
                log("no response",self.addr,reg,resp)
                return None

            # ---- 丢弃回显，只保留最后 8 个字节 ----
            if len(resp) > 8:
                resp = resp[-8:]

            # 响应帧格式: SYNC, SLAVE, REG, DATA3, DATA2, DATA1, DATA0, CRC
            data_bytes = resp[3:7]
            value = (data_bytes[0] << 24) | (data_bytes[1] << 16) | (data_bytes[2] << 8) | data_bytes[3]
            return value
        except Exception as e:
            log("Fail to read register:", self.addr, reg, e)
            return None

    # 写入寄存器
    def write_register(self, reg, value):
        try:
            sync = 0x05
            reg_addr = (reg & 0x7F) | 0x80  # 写操作 bit7=1
            data = [
                (value >> 24) & 0xFF,
                (value >> 16) & 0xFF,
                (value >> 8)  & 0xFF,
                value & 0xFF
            ]
            dat = [sync, self.addr, reg_addr] + data
            dat.append(self.calc_crc(dat))
            self.uart.write(bytearray(dat))
            # log("uart.write", dat)
        except Exception as e:
            log("Fail to write register:", self.addr, reg, value, e)

    # 读取SG_RESULT
    def read_sg_result(self):
        return self.read_register(0x41) & 0x3FF # type: ignore

    # 读取TSTEP
    def read_tstep(self):
        tstep_val = self.read_register(0x12) & 0xFFFFF # type: ignore
        CALIB_K = 20000 / 26490  # 魔法参数，实测校准值（设定PWM频率/TCM2209返回频率）
        
        # 当电机停止或速度很慢时(<15), tstep_val溢出
        if tstep_val == 0xFFFFF:
            return 0
        # 计算步进频率
        else:
            f_step = int(16_000_000 / tstep_val * CALIB_K)
        return f_step

    # 初始化
    def init_tmc2209(self, 
                     gconf_i_scale_analog:int =1,
                     gconf_internal_Rsense:int =1,
                     gconf_en_SpreadCycle:int =0,
                     gconf_pdn_disable:int =1,
                     gconf_mstep_reg_select:int =1,
                     gconf_outtime:int =5,
                     ihold:int =0,
                     irun_limit_check:int =20,
                     irun:int =20,
                     iholddelay:int =1,
                     tcool_threshold:int =200000,
                     sg_threshold:int =config.RETURN_TO_ZERO_SGTHRS,
                     chopconf_mres_limit_check:int =config.RETURN_TO_ZERO_MERS,
                     chopconf_mres:int =16,
                     chopconf_toff:int =3,
                     chopconf_hstrt:int =4,
                     chopconf_hend:int =2
                     ):
        '''
        1. 要启用StealthChop 斩波模式，保持GCONF寄存器的bit2=0
        2. 关闭pdn，保持GCONF寄存器的bit6=1
        3. 由于需要多电机控制，因此需要设定MS1,MS2为地址，细分由MRES寄存器决定，bit7=1
        4. 高速模式（高频PWM+低细分）进行堵转检测，实测 MRES = 0b0010，即8微步，比较合理
        5. 堵转阈值：根据 SG_RESULT > 2*SGTHRS 触发 DIAG，因此需要读取 SG_RESULT 判断细分、速度、SGTHRS设定是否合理
        6. TSTEP 是按照256微步计算的，实际的驱动步数是 TSTEP/(256/MRES)，才能得到实际步进频率
        7. TCOOLTHRS ≤ TSTEP，否则 SG 不启用，因为当电机的速度（TSTEP）低于 TCOOLTHRS 时，CoolStep 和 StallGuard 功能无法可靠工作。
            只有当速度超过 TCOOLTHRS 时，StallGuard 的失步检测信号才会输出到 DIAG 引脚，并且 CoolStep 功能才会被启用。
            因此，TCOOLTHRS越小，堵转检测越灵敏。
        8. IHOLD：保持电流（空闲时电流），范围 0~31
        9. IRUN：运行电流（正常运动电流），范围 0~31
        10. IHOLDDELAY：电流下降延时，范围 0~31

        参数：
        gconf_en_SpreadCycle：default=0
        gconf_pdn_disable：default=1
        gconf_mstep_reg_select：default=1
        gconf_internal_Rsense：default=0
        gconf_i_scale_analog：default=1
        ihold：default=8
        irun：default=31
        iholddelay：default=5
        tcool_threshold：default=200000
        sg_threshold：default=100
        chopconf_mers_run:default=256
        chopconf_mers_limit_check:default=8
        chopconf_toff:default=3
        chopconf_hstrt:default=4
        chopconf_hend:default=2
        '''
        # 记录初始化参数
        self.gconf_i_scale_analog = gconf_i_scale_analog
        self.gconf_internal_Rsense = gconf_internal_Rsense
        self.gconf_en_SpreadCycle = gconf_en_SpreadCycle
        self.gconf_pdn_disable = gconf_pdn_disable
        self.gconf_mstep_reg_select = gconf_mstep_reg_select
        self.ihold = ihold
        self.irun_limit_check = irun_limit_check
        self.irun = irun
        self.iholddelay = iholddelay
        self.tcool_threshold = tcool_threshold
        self.sg_threshold = sg_threshold
        self.chopconf_mres_limit_check = chopconf_mres_limit_check
        self.chopconf_mres = chopconf_mres
        self.chopconf_toff = chopconf_toff
        self.chopconf_hstrt = chopconf_hstrt
        self.chopconf_hend = chopconf_hend
        try:
            # ========== GCONF (0x00) 配置 ==========
            # bit7: mstep_reg_select = 1 → 细分由寄存器 MRES 决定
            # bit6: pdn_disable      = 1 → 允许 UART
            # bit2: en_SpreadCycle   = 0 → 不启用，需要使用 StealthChop 斩波模式
            # bit1: internal_Rsense  = 1 → 是否使用内部 Rsense 电阻，检测电流
            # bit0: i_scale_analog   = 1 → 使用 VREF 电位器作为电压基准（默认为1）
            # 默认值
            GCONF_val = 0b11000011
            for v in [gconf_mstep_reg_select,
                      gconf_pdn_disable,
                      gconf_en_SpreadCycle,
                      gconf_internal_Rsense,
                      gconf_i_scale_analog
                      ]:
                if v not in (0, 1):
                    raise ValueError("参数必须为0或1")
                    # 构造 GCONF_val
            GCONF_val = (
                (gconf_mstep_reg_select << 7) |
                (gconf_pdn_disable << 6) |
                (gconf_en_SpreadCycle << 2) |
                (gconf_internal_Rsense << 1) |
                (gconf_i_scale_analog << 0)
            )
            log(f'set GCONF_val={GCONF_val:0b}')
            now_time = time.time()
            while self.read_register(0x00) != GCONF_val:
                log(f'set GCONF_val={GCONF_val:0b}')
                self.write_register(0x00, value=GCONF_val)
                time.sleep(0.1)
                # 如果寄存器值仍未更新，则抛出异常
                if time.time() - now_time > gconf_outtime:
                    raise RuntimeError("GCONF寄存器配置失败")
                else:
                    break
            # 打印寄存器配置，二进制显示
            log(f"GCONF: {self.read_register(0x00):0b}")

            # ========== IHOLD_IRUN (0x10) 电流设置 ==========
            # IHOLD      = 保持电流（空闲时电流，避免发热）
            # IRUN       = 运行电流（正常运动电流）
            # IHOLDDELAY = 电流下降延时，越大越平滑
            IHOLD = ihold          # 推荐 5~10
            IRUN = irun_limit_check          # 推荐 20~30，太大会发热
            IHOLDDELAY = iholddelay     # 推荐 4~6

            IHOLD_IRUN_val = (IHOLDDELAY << 16) | (IRUN << 8) | IHOLD
            self.write_register(0x10, IHOLD_IRUN_val)

            # ========== TCOOLTHRS (0x14) 堵转检测速度阈值 ==========
            # 必须小于 TSTEP，否则 SG 不启用
            TCOOLTHRS = tcool_threshold
            self.write_register(0x14, TCOOLTHRS)

            # ========== SGTHRS (0x40) 堵转灵敏度 ==========
            # 0~255，值越大越容易触发。推荐 16~64 之间调试。
            SGTHRS = sg_threshold
            self.write_register(0x40, SGTHRS)

            # ========== CHOPCONF (0x6C) 细分 + 斩波器配置 ==========
            #MRES = 0b1000  # 8 微步（更常用，比 256 微步更稳）
            MRES = self.microsteps_tab[chopconf_mres_limit_check]
            TOFF = chopconf_toff # 设置斩波器的关断时间，影响电流衰减过程，不能为 0，推荐 3~5
            HSTRT = chopconf_hstrt # 设置斩波器的滞回起点，影响电流上升过程，推荐 4~6
            HEND = chopconf_hend # 设置斩波器的滞回终点，影响电流下降过程，推荐 2~4

            CHOPCONF_val = (MRES << 24) | (HEND << 7) | (HSTRT << 4) | TOFF
            self.write_register(0x6C, CHOPCONF_val)
            
            # 结束
            self.init_success = True
            return True

        except Exception as e:
            log(f"Fail to configure: {e}")
            self.init_success = False
            return False

    # 细分设置
    def set_microstep(self, microsteps:int = 256,chopconf_toff:int =3, chopconf_hstrt:int =4, chopconf_hend:int =2, en_double_edge_step:bool =False):
        if microsteps not in self.microsteps_tab:
            raise ValueError("Invalid microsteps setting")
        
        MRES = self.microsteps_tab[microsteps]
        TOFF = chopconf_toff # 设置斩波器的关断时间，影响电流衰减过程，不能为 0，推荐 3~5
        HSTRT = chopconf_hstrt # 设置斩波器的滞回起点，影响电流上升过程，推荐 4~6
        HEND = chopconf_hend # 设置斩波器的滞回终点，影响电流下降过程，推荐 2~4
        DEDGE = 1 if en_double_edge_step else 0  # 双边沿步进,在第29bit

        CHOPCONF_val = (DEDGE << 29) | (MRES << 24) | (HEND << 7) | (HSTRT << 4) | TOFF
        self.write_register(0x6C, CHOPCONF_val)

    # 设置电流
    def set_current(self, hold_current:int =2, run_current:int =15, iholddelay:int =4):
        '''
        hold_current: 0-31
        run_current: 0-31
        iholddelay: 0-31
        '''
        IHOLD = hold_current
        IRUN = run_current
        IHOLDDELAY = iholddelay

        IHOLD_IRUN_val = (IHOLDDELAY << 16) | (IRUN << 8) | IHOLD
        self.write_register(0x10, IHOLD_IRUN_val)

    # 启用/禁用 SpreadCycle
    def set_en_SpreadCycle(self, en: int =1):
        # ========== GCONF (0x00) 配置 ==========
        # bit2: en_SpreadCycle   = 1 → 启用，需要使用 StealthChop 斩波模式
        # 其他保持默认值
        en_SpreadCycle = en
        for v in [self.gconf_mstep_reg_select,
                    self.gconf_pdn_disable,
                    en_SpreadCycle,
                    self.gconf_internal_Rsense,
                    self.gconf_i_scale_analog
                    ]:
            if v not in (0, 1):
                raise ValueError("参数必须为0或1")
                # 构造 GCONF_val
        GCONF_val = (
            (self.gconf_mstep_reg_select << 7) |
            (self.gconf_pdn_disable << 6) |
            (en_SpreadCycle << 2) |             # 修改这一位
            (self.gconf_internal_Rsense << 1) |
            (self.gconf_i_scale_analog << 0)
        )
        now_time = time.time()
        while self.read_register(0x00) != GCONF_val:
            self.write_register(0x00, value=GCONF_val)
            time.sleep(0.1)
            # 如果寄存器值仍未更新，则抛出异常
            if time.time() - now_time > 1:
                raise RuntimeError("GCONF寄存器配置失败")
            else:
                break



# debug:

if __name__ == "__main__":
    import serial
    # 定义一个uart
    uart = serial.Serial("/dev/serial0", baudrate=115200, timeout=0)

    log("=== TMC2209 Motor Driver Test ===")
    # log("x轴地址:", hex(config.UART_X_ADDR))
    # log("y轴地址:", hex(config.UART_Y_ADDR))
    # log("z轴地址:", hex(config.UART_Z_ADDR))

    x_tmc = TMC2209(uart, 0x00)
    y_tmc = TMC2209(uart, 0x01)
    z_tmc = TMC2209(uart, 0x02)


    x_tmc.init_tmc2209(chopconf_mres_limit_check=config.RETURN_TO_ZERO_MERS)
    time.sleep(1)
    y_tmc.init_tmc2209(chopconf_mres_limit_check=config.RETURN_TO_ZERO_MERS)
    time.sleep(1)
    z_tmc.init_tmc2209(chopconf_mres_limit_check=config.RETURN_TO_ZERO_MERS)
    time.sleep(1)

    # x_tmc.set_microstep(16,en_double_edge_step=True)
    # y_tmc.set_microstep(16,en_double_edge_step=True)
    # z_tmc.set_microstep(16,en_double_edge_step=True)

    # x_tmc.set_current(hold_current=2, run_current=20, iholddelay=4)
    # y_tmc.set_current(hold_current=2, run_current=20, iholddelay=4)
    # z_tmc.set_current(hold_current=2, run_current=20, iholddelay=4)

    # ========== GPIO 初始化 ==========
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    for pin in [X_DIR, Y_DIR, Z_DIR, X_EN, Y_EN, Z_EN]:
        GPIO.setup(pin, GPIO.OUT)

    # 默认状态
    GPIO.output([X_DIR, Y_DIR, Z_DIR], GPIO.LOW)
    GPIO.output([X_EN, Y_EN, Z_EN], GPIO.HIGH)  # 高电平关闭使能

    # 使用PWM控制PULS引脚
    for pin in [X_PULS, Y_PULS, Z_PULS]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
        GPIO.PWM(pin, 1000).start(0)  # 初始频率1kHz，占空比0

    def run_motor(direction, freq, run_time=2):
        """让电机以指定方向、频率运行 run_time 秒"""
        GPIO.output(X_DIR, direction)
        pwm_x = GPIO.PWM(X_PULS, freq)
        pwm_x.start(50)  # 占空比50%

        GPIO.output(Y_DIR, direction)
        pwm_y = GPIO.PWM(Y_PULS, freq)
        pwm_y.start(50)  # 占空比50%

        # GPIO.output(Z_DIR, direction)
        # pwm_z = GPIO.PWM(Z_PULS, freq)
        # pwm_z.start(50)  # 占空比50%

        time.sleep(0.1)  # 稳定等待

        start = time.monotonic()
        while (time.monotonic() - start) < run_time:
            # 每 200ms 打印一次 SG_RESULT + DIAG
            log("当前方向:", direction)
            log(f"X_TSTEP:{x_tmc.read_tstep()}, X_SG:{x_tmc.read_sg_result()}"
                # f"Y_TSTEP:{y_tmc.read_tstep()}, Y_SG:{y_tmc.read_sg_result()},"
                f"Z_TSTEP:{z_tmc.read_tstep()}, Z_SG:{z_tmc.read_sg_result()}")
            time.sleep(0.2)  # 200ms
        


    # GPIO.output(X_EN, GPIO.LOW)  # 低电平使能
    GPIO.output([X_EN, Y_EN, Z_EN], GPIO.LOW)  # 高电平关闭使能

    try:
        # while True:
        #     # 正转 2 秒
        #     run_motor(1, 10000, run_time=2)
        #     run_motor(0, 10000, run_time=2)
        pass
    except KeyboardInterrupt:
        GPIO.output([X_DIR, Y_DIR, Z_DIR], GPIO.LOW)
        GPIO.output([X_EN, Y_EN, Z_EN], GPIO.HIGH)  # 高电平关闭使能
        log("STOP")
