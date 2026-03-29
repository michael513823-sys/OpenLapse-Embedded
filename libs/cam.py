from picamera2 import Picamera2 # type: ignore
import datetime, time
import subprocess

# 初始化摄像头
picam = Picamera2()
# 创建两个分辨率的配置
cam_config = picam.create_still_configuration(
    main={"size": (4056, 3040), "format": "BGR888"},
    lores={"size": (160, 120), "format": "YUV420"},
    controls={"FrameDurationLimits": (33333, 33333), "AeEnable": True},
    display=None
)
picam.configure(cam_config)
picam.start(show_preview=False)
# 等待摄像头启动
time.sleep(2)
print("[INFO] Camera started.")


# 捕获图像
def capture_image(res="main"):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"/home/pi/timelapse/imgs/{ts}_{res}.jpg"
    if res == "lores":
        # 捕获低分辨率图像
        picam.capture_file(path, name="lores")
    # 否则捕获高分辨率图像
    else:
        picam.capture_file(path, name="main")
    print(f"[CAPTURE] {res} Saved {path}")


# 接收端 IP 和端口
DEST_IP = "192.168.1.218"
DEST_PORT = 5000

# 使用树莓派硬件编码器：h264_v4l2m2m
cmd = [
    "ffmpeg",
    "-f", "rawvideo", # 输入格式
    "-pix_fmt", "yuv420p",      # 与 lores 对应
    "-s", "160x120", # 分辨率
    "-r", "10", # 帧率
    "-i", "-", # 从标准输入读取
    "-c:v", "h264_v4l2m2m", # 使用树莓派硬件编码器
    "-b:v", "500k", # 码率
    "-preset", "ultrafast", # 编码速度
    "-tune", "zerolatency", # 低延迟
    "-g", "5", # 关键帧间隔
    "-bufsize", "0", # 不使用缓冲
    "-flags", "low_delay", # 低延迟
    "-fflags", "nobuffer", # 减少延迟
    "-f", "mpegts", # 输出格式
    f"udp://{DEST_IP}:{DEST_PORT}?pkt_size=1200&max_delay=0"
]




if __name__ == "__main__":
    # 打印本机 IP 地址
    # 示例：捕获一张高分辨率图像
    # capture_image("main")
    # 示例：捕获一张低分辨率图像
    # capture_image("lores")

    # print("[INFO] Program finished.")

    # picam.stop()

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    # 推流循环
    try:
        while True:
            frame = picam.capture_array("lores")
            proc.stdin.write(frame.tobytes())
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        proc.stdin.close()
        proc.wait()
