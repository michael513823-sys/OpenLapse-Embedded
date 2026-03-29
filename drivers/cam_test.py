import time

print("Testing OpenCV import...")
now = time.time()
import cv2
print("Import took {:.2f} seconds".format(time.time() - now))
print("opencv version:", cv2.__version__)



now = time.time()
print("Testing picamera2 import...")
from picamera2 import Picamera2
# import picamera2

picam2 = Picamera2()  # 初始化相机
print("Import took {:.2f} seconds".format(time.time() - now))

# picamera2 没有 __version__，但可以查模块的元数据
import importlib.metadata
print("picamera2 version:", importlib.metadata.version("picamera2"))
