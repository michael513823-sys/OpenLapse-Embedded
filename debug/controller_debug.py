from machine import I2C, Pin
import time
from lib.ads1115 import ADS1115

# 按你的连线修改
i2c = I2C(0, scl=Pin(23), sda=Pin(22), freq=400000)

# 如果 ADDR 接 GND，地址是 0x48；如接 VDD 则为 0x49
ads = ADS1115(i2c, addr=0x48, gain=1, sps=860)  # 0~3.3V 推荐 gain=1

def read_all(avg=8, delay_ms=2):
    """多次采样做简单平均，降低抖动；对None安全。"""
    sums = [0.0, 0.0, 0.0, 0.0]
    n = 0
    for _ in range(avg):
        vals = ads.read_all_raws()
        # 若中间出错/返回异常，直接跳过该次
        if not vals or len(vals) != 4:
            continue
        for i in range(4):
            # 防守式：遇到负/NaN（极少见）做截断
            v = vals[i]
            if v is None or v != v:
                v = 0.0
            if v < 0:
                v = 0.0
            sums[i] += v
        n += 1
        time.sleep_ms(delay_ms)
    if n == 0:
        return [None, None, None, None]
    return [s / n for s in sums]

while True:
    v = read_all(avg=8, delay_ms=1)
    v0, v1, v2, v3 = v
    print("A0={:.4f}  A1={:.4f}  A2={:.4f}  A3={:.4f}".format(
        v0 or 0.0, v1 or 0.0, v2 or 0.0, v3 or 0.0))
    #time.sleep(0.05)
