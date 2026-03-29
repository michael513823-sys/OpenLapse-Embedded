
import time

class PWMPlayer:
    def __init__(self, motor):
        self.motor = motor
    

    def power_on(self):
        # --- 旋律（节拍值）---
        melody_f = [
            ("G4", 1), ("G4", 0.5), #("A4", 0.5), ("D4", 1),
            # ("C4", 1), ("C4", 0.5), ("A3", 0.5), ("D4", 1),
        ]
        melody_b = [
            # ("G4", 1), ("G4", 0.5), ("A4", 0.5), ("D4", 1),
            ("C4", 1), ("C4", 0.5), #("A3", 0.5), ("D4", 1),
        ]
        self.play(melody_f, melody_b)

    def network_connected(self):
        melody_f = [
            ("G4", 1), ("G4", 0.5), 
        ]
        melody_b = [
            ("D4", 0.5), ("D4", 1)
        ]
        self.play(melody_f, melody_b)

    def controller_connected(self):
        melody_f = [
            ("C4", 1), ("C4", 0.5), 
        ]
        melody_b = [
            ("D4", 0.5), ("D4", 1)
        ]
        self.play(melody_f, melody_b,bpm=360)
    
    # 正反方向放歌
    def play(self,f,b,bpm=180):
        self.motor.set_current(irun=31, ihold=1, delay=4)
        self.motor.set_microsteps(2)
        self.motor.enable_motor(True)

        # 开启spreadcycle，声音大
        self.motor.en_spreadcycle(True)
        self.play_pwm(f, bpm, direction=1)
        # time.sleep(0.5)
        self.play_pwm(b, bpm, direction=0)

        # 改回16
        self.motor.set_microsteps(16)

        # 关闭spreadcycle
        self.motor.en_spreadcycle(False)

        self.motor.enable_motor(False)
        time.sleep(0.5)

    def play_pwm(self, melody, bpm=120, direction=0):
        """让步进电机播放《东方红》开头片段"""

        # --- 仅保留用到的音符 ---
        note_freqs = {
            "A3": 220,
            "C4": 262,
            "D4": 294,
            "G4": 392,
            "A4": 440,
            "REST": 0
        }
        # --- 播放参数 ---
        duty = 50
        gap_ratio = 0.1
        beat_time = 60.0 / bpm  # 每拍秒数

        # --- 播放循环 ---
        for note, beats in melody:
            freq = note_freqs[note]
            duration = beats * beat_time

            if freq == 0:
                time.sleep(duration)
            else:
                # 播放音符
                self.motor.run_motor_pwm(freq=freq * 0.5, duty_cycle=duty, direction=direction)
                time.sleep(duration)
                self.motor.stop_motor_pwm()

            # 节拍间歇（自动随BPM变化）
            gap = beat_time * gap_ratio
            time.sleep(gap)

if __name__ == "__main__":
    import serial # type: ignore
    from motor import MotorController # type: ignore
    uart = serial.Serial("/dev/serial0", baudrate=115200, timeout=0)
    X_DIR = 17
    X_PULS = 18
    X_EN = 5
    x_motor = MotorController(uart, 0x02, dir_pin=X_DIR, pulse_pin=X_PULS, enable_pin=X_EN)
    player = PWMPlayer(x_motor)
    player.power_on()
    time.sleep(2)
    player.network_connected()
    time.sleep(2)
    player.controller_connected()
