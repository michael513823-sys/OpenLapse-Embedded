import time
import serial

# ========== BCM 引脚编号 ==========
PITX  = 14
PIRX  = 15


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


for addr in [0x00,0x01,0x02]:
    print('地址：',addr)
    frame = [0x05, addr, 0x00]  # 示例数据
    crc = calc_crc(frame)
    frame.append(crc)
    print("发送:", [hex(x) for x in frame])
    uart.write(bytearray(frame))

    resp = uart.read(16)
    # print("响应:", resp)

    if len(resp) >= len(frame):
        # 去掉回显
        resp = resp[len(frame):]
        print("实际响应:", resp)



print("测试完成")

