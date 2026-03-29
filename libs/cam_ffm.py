from picamera2 import Picamera2  # type: ignore
import cv2
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import numpy as np
import signal
import sys


# =====================================================
#                      Camera 类
# =====================================================
class Camera:
    def __init__(self, width=640, height=480, show_timestamp=True, fps=30):
        self.picam = Picamera2()
        self.config = self.picam.create_video_configuration(
            main={"size": (width, height), "format": "BGR888"},
            # controls={"FrameDurationLimits": (int(1e6 / fps), int(1e6 / fps))}
        )
        self.picam.configure(self.config)
        self.picam.start()

        self.frame = np.zeros((height, width, 3), dtype=np.uint8)
        self.lock = threading.Lock()
        self.running = True
        self.fps = fps
        self.show_timestamp = show_timestamp
        self.width, self.height = width, height

        self.thread = threading.Thread(target=self._update_frame, daemon=True)
        self.thread.start()
        print("[INFO] Camera initialized and capture thread started.")

    # 带帧率限制
    def _update_frame(self):
        interval = 1 / self.fps
        while self.running:
            try:
                raw = self.picam.capture_array("main")
                if raw is None:
                    continue
                if self.show_timestamp:
                    frame = raw.copy()
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    text = f"{timestamp} {self.fps}FPS {self.width}x{self.height}"
                    cv2.putText(frame, text, (10, 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                else:
                    frame = raw.copy()

                with self.lock:
                    self.frame = frame
            except Exception as e:
                print(f"[ERROR] Camera capture error: {e}")
                self.picam.stop()
                time.sleep(1)
                self.picam.start()
            time.sleep(interval)
    
    # 获取当前帧的JPEG编码
    def get_jpeg(self):
        with self.lock:
            frame_copy = self.frame.copy()
        for _ in range(2):  # 失败重试
            ret, buf = cv2.imencode(".jpg", frame_copy, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ret:
                return buf.tobytes()
        raise RuntimeError("JPEG encode failed")

    def stop(self):
        """安全停止"""
        self.running = False
        self.thread.join(timeout=1)
        self.picam.stop()
        print("[INFO] Camera stopped.")


# =====================================================
#                     HTTP 服务器
# =====================================================
class StreamingHandler(BaseHTTPRequestHandler):
    def _html_page(self):
        """生成主页HTML"""
        return f"""
        <html>
        <head><title>OpenLapse Stream</title></head>
        <body>
            <h1>OpenLapse Camera Stream</h1>
            <img src="/stream.mjpg" width="{camera.width}" height="{camera.height}">
        </body>
        </html>
        """.encode()

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(self._html_page())

        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()

            try:
                while True:
                    frame = camera.get_jpeg()
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(frame)))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
                    time.sleep(1 / camera.fps)
            except (BrokenPipeError, ConnectionResetError):
                print("[WARN] Client disconnected.")
            except Exception as e:
                print(f"[ERROR] Streaming error: {e}")

        elif self.path.startswith('/set'):
            from urllib.parse import urlparse, parse_qs
            query = parse_qs(urlparse(self.path).query)
            try:
                controls = {}
                if "exposure" in query:
                    exposure = int(query["exposure"][0])
                    controls["ExposureTime"] = exposure  # 微秒
                if "gain" in query:
                    gain = float(query["gain"][0])
                    controls["AnalogueGain"] = gain
                if "awb" in query:
                    awb = query["awb"][0]
                    if awb.lower() == "off":
                        controls["AwbEnable"] = False
                    else:
                        controls["AwbEnable"] = True
                if "awb_mode" in query:
                    controls["AwbMode"] = query["awb_mode"][0]

                if controls:
                    camera.picam.set_controls(controls)
                    msg = f"[INFO] Controls updated: {controls}"
                    print(msg)
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(msg.encode())
                else:
                    self.send_error(400, "No valid control parameters.")
            except Exception as e:
                self.send_error(500, f"Error setting controls: {e}")

        elif self.path == '/status':
            controls = camera.picam.capture_metadata()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            import json
            self.wfile.write(json.dumps(controls, indent=2).encode())

        else:
            self.send_error(404)
            self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


# =====================================================
#                     主运行逻辑
# =====================================================
# def run_server(host='0.0.0.0', port=8081):
#     global camera
#     camera = Camera(width=1280, height=960)
#     server = ThreadedHTTPServer((host, port), StreamingHandler)

#     def shutdown(*args):
#         print("\n[INFO] Shutting down server...")
#         # 在新线程中调用 shutdown()，避免主线程阻塞
#         threading.Thread(target=server.shutdown, daemon=True).start()
#         camera.stop()
#         sys.exit(0)

#     signal.signal(signal.SIGINT, shutdown)
#     signal.signal(signal.SIGTERM, shutdown)

#     print(f"[INFO] MJPEG server running at: http://{host}:{port}/")
#     try:
#         server.serve_forever()
#     except KeyboardInterrupt:
#         pass
#     finally:
#         print("[INFO] Server terminated.")


# =====================================================
#                 推流控制类（开启/关闭）
# =====================================================
class MJPEGStreamController:
    def __init__(self, host='0.0.0.0', port=8081,
                 width=1280, height=960, fps=30, show_timestamp=True):
        self.host = host
        self.port = port
        self.width = width
        self.height = height
        self.fps = fps
        self.show_timestamp = show_timestamp

        self.server: ThreadedHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._started_evt = threading.Event()
        self._stopped_evt = threading.Event()
        self._serve_exc: Exception | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and self.server is not None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def _serve(self):
        """在后台线程中启动服务器并阻塞运行，直到 shutdown() 被调用"""
        global camera
        self._serve_exc = None
        self._stopped_evt.clear()
        try:
            # 创建 Camera 与 Server
            camera = Camera(width=self.width, height=self.height, show_timestamp=self.show_timestamp, fps=self.fps)
            self.server = ThreadedHTTPServer((self.host, self.port), StreamingHandler)
            self._started_evt.set()
            print(f"[INFO] MJPEG server running at: {self.url}")

            # 阻塞直到 shutdown 调用
            self.server.serve_forever()
        except Exception as e:
            self._serve_exc = e
            print(f"[ERROR] Server serve_forever exception: {e}")
        finally:
            # 优雅收尾：关闭 server 与 camera
            try:
                if self.server is not None:
                    self.server.server_close()
            except Exception as e:
                print(f"[WARN] server_close error: {e}")
            try:
                if 'camera' in globals() and camera is not None:
                    camera.stop()
            except Exception as e:
                print(f"[WARN] camera.stop error: {e}")
            self.server = None
            self._stopped_evt.set()
            print("[INFO] Server thread terminated.")

    def start(self, wait_ready: float = 2.0) -> bool:
        """启动推流。如果端口被占用或启动失败，返回 False。"""
        if self.is_running:
            print(f"[INFO] Stream already running at {self.url}")
            return True

        self._started_evt.clear()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

        # 等待最多 wait_ready 秒确认启动（绑定端口 & 线程进入运行）
        if not self._started_evt.wait(timeout=wait_ready):
            print("[ERROR] Stream start timed out.")
            return False

        if self._serve_exc:
            print(f"[ERROR] Stream failed to start: {self._serve_exc}")
            return False

        print(f"[OK] Stream started at {self.url}")
        return True

    def stop(self, join_timeout: float = 3.0) -> bool:
        """停止推流；返回是否已停止。"""
        if not self.is_running:
            print("[INFO] Stream is not running.")
            return True

        try:
            # 触发服务器优雅退出
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        except Exception as e:
            print(f"[ERROR] server.shutdown error: {e}")

        # 等待线程退出
        if self._thread is not None:
            self._thread.join(timeout=join_timeout)

        if self._thread is not None and self._thread.is_alive():
            print("[WARN] Server thread did not stop in time.")
            return False

        self._thread = None
        print("[OK] Stream stopped.")
        return True

    def restart(self) -> bool:
        ok = self.stop()
        if not ok:
            return False
        return self.start()

    def status(self) -> str:
        return f"running @ {self.url}" if self.is_running else "stopped"

if __name__ == "__main__":
    controller = MJPEGStreamController(host='0.0.0.0', port=8081, width=1280, height=960, fps=30, show_timestamp=True)
    controller.start()
    print(controller.status())      # -> running @ http://0.0.0.0:8081/
    # time.sleep(1000*60)
    # controller.stop()
    # print(controller.status())      # -> stopped
    while True:
        time.sleep(1)