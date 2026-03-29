from picamera2 import Picamera2 # type: ignore
import time
import subprocess
import cv2
import numpy as np
import threading
import os

class Camera:
    def __init__(self):
        # 初始化摄像头
        self.picam = Picamera2()
        # 建立两种分辨率的配置
        self.lores_config = self.picam.create_video_configuration(
            main={"size": (640, 480), "format": "BGR888"},
            controls={"FrameDurationLimits": (33333, 33333)}  # 30fps
        )
        self.hires_config = self.picam.create_video_configuration(
            main={"size": (3280, 2464), "format": "BGR888"},
            controls={"FrameDurationLimits": (33333, 33333)}  # 30fps
        )
        # 当前分辨率状态, 相机是否启动
        self.is_lores, self.is_running = True, False
        # 默认使用低分辨率启动
        self._start(self.lores_config)

        # 最新的一帧lores图像
        self.last_lores = np.zeros((480, 640, 3), dtype=np.uint8)
        

    # 启动摄像头，带配置参数
    def _start(self, config):
        if self.is_running:
            return
        self.picam.configure(config)
        self.picam.start()
        self.is_running = True
        print('_start')
    
    # 停止摄像头
    def _stop(self):
        if not self.is_running:
            return
        self.picam.stop()
        self.is_running = False
        print('_stop')

    # 切换到低分辨率
    def _change_lores(self):
        if self.is_lores:
            return
        self._stop()
        self._start(self.lores_config)
        self.is_lores = True
        print('_change_lores')

    # 切换到高分辨率
    def _change_hires(self):
        if not self.is_lores:
            return
        self._stop()
        self._start(self.hires_config)
        self.is_lores = False
        print('_change_hires')
    
    # 调整相机参数
    def set_controls(self, controls: dict):
        self.picam.set_controls(controls)

    # 捕获低分辨率图片，在高配置时不断流
    def capture_lores(self):
        if self.is_lores:
            img = self.picam.capture_array("main")
            self.last_lores = img
        else:
            # img = self.last_lores
            img = self.last_lores.copy()
        
        _img = img.copy()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        cv2.putText(_img, f"{timestamp}", (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        return _img

    # 捕获高分辨率图片
    def capture_hires(self):
        self._change_hires()
        img = self.picam.capture_array("main")
        self._change_lores()
        return img


# 处理和保存图片的类
class ImageProcessor:
    def __init__(self,
                 save_path="/home/pi/timelapse/imgs/",
                 expi_name="unkonw_expi",
                 well_name="unkonw_well",
                 filename_prefix="unkonw_prefix",
                 format = "PNG"
                 ):
        # 参数
        self.save_path = save_path
        self.expi_name = expi_name
        self.well_name = well_name
        self.filename_prefix = filename_prefix
        self.format = format
    
    # 设置参数
    def set_params(self, params: dict):
        """设置参数
        params: 字典，包含需要设置的参数
        参数包括：
            save_path: 保存路径
            expi_name: 实验名称
            well_name: 井名称
            filename_prefix: 文件名前缀
            format: 图片格式，PNG或JPG
        默认值：
            params = {"save_path": "/home/pi/timelapse/imgs/",
                      "expi_name": "unkonw_expi",  # 根据实验类型改为transwell or scratch等
                      "well_name": "unkonw_well",
                      "filename_prefix": "",
                      "format": "PNG"}
            image_processor.set_params(params)
        这样就会将参数设置为指定的值。
        拍摄结果将保存到： /home/pi/timelapse/imgs/unkonw_expi/unkonw_well/snapshot_YYYYMMDD_HHMMSS.png
        """
        for key, value in params.items():
            # check if the attribute exists
            if not hasattr(self, key):
                print(f"[WARN] unknown parameter: {key}")
                continue
            # only set if value is not None or empty
            if value is not None and value != "":
                try:
                    # set attribute
                    setattr(self, key, value)
                except Exception as e:
                    print(f"[ERROR] set {key} failed: {e}")


    # 同步保存
    def _save_image(self, img):
        """后台线程函数：保存PNG图片"""
        # 如果目录不存在，则创建目录
        file_path = os.path.join(self.save_path, self.expi_name, self.well_name)
        # file_path= f"{self.save_path}/{self.expi_name}/{self.well_name}/"
        os.makedirs(file_path, exist_ok=True)

        # 生成文件名
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        # if self.filename_prefix:
        #     filename = f"{self.filename_prefix}_{timestamp}.{self.format.lower()}"
        # else:
        #     filename = f"{timestamp}.{self.format.lower()}"
        filename = f"{self.filename_prefix}_{timestamp}.{self.format.lower()}"

        # 完整路径
        _filename = os.path.join(file_path, filename)

        # 保存图片为PNG或JPG或其他格式try:
        try:
            if self.format.upper() in ["JPG", "JPEG"]:
                cv2.imwrite(_filename, img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            elif self.format.upper() == "BMP":
                cv2.imwrite(_filename, img)
            elif self.format.upper() == "TIFF":
                cv2.imwrite(_filename, img)
            else:
                cv2.imwrite(_filename, img, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            # print(f"[✅] 已保存图片: {_filename}")
        except Exception as e:
            print(f"保存图片失败: {e}")
        # print(f"[✅] 异步保存完成: {filename}")

    # 异步保存
    def save_image_async(self,img):
        """启动后台线程保存图片"""
        threading.Thread(target=self._save_image, args=(img,), daemon=True).start()



class RMTPStreamer:
    def __init__(self, rtmp_url: str="rtmp://localhost/live/stream"):
        """初始化 RTMP 推流器
        rtmp_url: RTMP 服务器地址，例如 "rtmp://localhost/live/stream"
        需要确保系统已安装 ffmpeg，并且支持 h264_v4l2m2m 编码器
        该类提供 start_stream() 和 stop_stream() 方法来控制推流
        
        例子：
        streamer = RMTPStreamer("rtmp://localhost/live/stream")
        streamer.start_stream()
        # 通过 streamer.proc.stdin.write(frame.tobytes()) 推送视频帧
        streamer.stop_stream()

        其中 frame 是一个 numpy 数组，格式为 BGR24，分辨率为 640x480
        该类会启动一个 ffmpeg 子进程，将通过 stdin 接收的视频帧推送到指定的 RTMP 服务器
        需要注意的是，推流过程中需要不断向 stdin 写入视频帧，否则推流会中断
        
        例如：
        frame = picam.capture_lores()  # 获取一帧图像
        streamer.proc.stdin.write(frame.tobytes())  # 推送视频帧

        该类适用于树莓派等设备，利用其硬件 H.264 编码器进行高效推流
        """
        self.rtmp_url = rtmp_url
        self.proc = None
        self.time = None

    def start_stream(self):
        if self.proc is not None:
            print("[WARN] Stream already running.")
            return

        cmd = [
            "ffmpeg",
            "-f", "rawvideo",          # 输入类型：原始帧
            "-pix_fmt", "bgr24",     # 与摄像头格式对应bgr24
            "-s", "640x480",           # 分辨率
            "-r", "30",                # 帧率
            "-i", "-",                 # 从 stdin 接收输入
            "-c:v", "h264_v4l2m2m",    # 树莓派硬件 H.264 编码器
            "-b:v", "1000k",           # 码率
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-g", "10",
            "-f", "flv",               # RTMP 使用 FLV 容器
            self.rtmp_url
        ]

        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        print("[INFO] RTMP stream started.")

    def stop_stream(self):
        if self.proc is None:
            print("[WARN] No stream to stop.")
            return

        self.proc.stdin.close() # type: ignore
        self.proc.wait()
        self.proc = None
        print("[INFO] RTMP stream stopped.")
    
    # 推送一帧视频
    def push_frame(self, frame):
        if self.proc is None:
            print("[ERROR] Stream not started.")
            return
        self.proc.stdin.write(frame.tobytes()) # type: ignore

    # 定时拍摄
    def snap_periodically(self, interval=10):
        """每隔 interval 秒拍摄一次图片"""
        if self.time is None:
            self.time = time.time()
            return False
        now = time.time()
        if now - self.time >= interval:
            self.time = now
            return True
        return False



if __name__ == "__main__":
    # 启动 RTMP 推流器
    wlan_host= 'localhost'
    rtmp_url = f"rtmp://{wlan_host}/live/stream"
    
    rtmp_streamer = RMTPStreamer(rtmp_url)
    rtmp_streamer.start_stream()

    # 启动摄像头
    picam = Camera()

    # 启动图片处理器
    image_processor = ImageProcessor()
    params = {
        "save_path": "/home/pi/timelapse/imgs/",
        "expi_name": "test_expi",
        "well_name": "test_well",
        "filename_prefix": "test_prefix",
        "format": "PNG"
    }
    image_processor.set_params(params)

    # 每10秒拍一次高分辨率照片
    last_snap = 0
    interval = 10
    # 是否捕获高分辨率图像
    capture = True
    try:
        while True:
            # 推流
            frame = picam.capture_lores()
            rtmp_streamer.push_frame(frame)
            time.sleep(1/60)

            # # 间隔拍照
            # if rtmp_streamer.snap_periodically(interval=interval) and capture:
            # # now = time.time()
            # # if (now - last_snap >= interval) and capture:
            # #     last_snap = now
            #     # 启动一个后台线程执行拍照，不阻塞主循环
            #     hres_img_array = picam.capture_hires()
            #     # 异步保存，不阻塞主线程
            #     # threading.Thread(target=save_image_async, args=(hres_img_array.copy(),), daemon=True).start()
            #     image_processor.save_image_async(hres_img_array)


    except KeyboardInterrupt:
        print("\n[STOP] 手动停止。")
    finally:
        rtmp_streamer.stop_stream()
        picam._stop()
        print("✅ 退出完成。")
