from picamera2 import Picamera2 # type: ignore
import datetime, time

# 初始化摄像头
picam = Picamera2()
# 创建两个分辨率的配置
cam_config = picam.create_still_configuration(
    main={"size": (4056, 3040), "format": "BGR888"},
    lores={"size": (640, 480), "format": "YUV420"},
    display=None
)
picam.configure(cam_config)
picam.start()
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





if __name__ == "__main__":
    # 打印本机 IP 地址
    # 示例：捕获一张高分辨率图像
    # capture_image("main")
    # 示例：捕获一张低分辨率图像
    capture_image("lores")

    print("[INFO] Program finished.")

    picam.stop()
