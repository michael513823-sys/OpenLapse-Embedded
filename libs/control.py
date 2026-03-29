import socket, threading
import time
import json
import queue

# UDP接收(非阻塞)
class UDPListener(threading.Thread):
    def __init__(self, 
                 port:int,   # 只需要监听端口
                 host:str='0.0.0.0',  # 监听所有本地地址
                 ):
        super().__init__(daemon=True)
        # 初始化UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        # 队列存放接收的命令
        self.queue = queue.Queue()
        # 控制运行标志
        self.running = True

    # 线程运行函数
    def run(self):
        # print(f"UDP监听启动：{self.sock.getsockname()}")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)  # 阻塞等待
                msg = data.decode().strip()
                try:
                    cmd = json.loads(msg)
                except json.JSONDecodeError:
                    print(f"无法解析JSON: {msg}")
                    continue

                # 附加元信息
                cmd["from"] = addr
                cmd["recv_time"] = str(time.time())

                # 放入队列中
                self.queue.put(cmd)
            except Exception as e:
                print("接收异常:", e)
                time.sleep(0.5)

    # 停止监听
    def stop(self):
        self.running = False
        self.sock.close()


class PCConnector:
    def __init__(self, 
                 rpi_name='OpenLapse',
                 controller_name='OpenLapse_Controller'
                 rpi_port=5005, 
                 single_send_ip=None, 
                 single_port=None, 
                 broadcast_ip='255.255.255.255',
                 broadcast_port=64565,
                 brodcast_interval=1):
        # 广播间隔，单位秒
        self.brodcast_interval = brodcast_interval

        # 网络参数信息
        self.rpi_ip = self._get_ip()
        self.rpi_port = rpi_port

        # 只发送给指定主机
        self.target_ip = target_ip
        self.target_port = target_port

        # 广播到局域网所有主机
        self.broadcast_ip = broadcast_ip  
        self.broadcast_port = broadcast_port

        # 工作参数信息
        self.status_dict = {
            1: "WAITING",    # 等待连接
            2: "CONNECTED",  # 已连接
            3: "CAPTURING",  # 拍摄中
            4: "MOVING",    # 运动中
            5: "ERROR",      # 错误
        }
        self.name = name  # 设备名称
        self.msg = ""  # 发送的信息
        self.status = "WAITING"  # 当前状态


        # 启动广播
        threading.Thread(target=self._udp_broadcast, daemon=True).start()
        # 监听来自控制端的消息
        self.target_listener = UDPListener(port=self.rpi_port)
        self.target_listener.start()



    # 获取本机 IP 地址
    def _get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # 连接到一个不会真的建立的外部地址，用于确定本地网卡
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip
    
    # 发送 UDP 广播消息
    def _udp_broadcast(self):
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                # 向局域网所有主机广播
                TARGET_IP = self.broadcast_ip
                # UDP广播端口(控制端监听该地址，获得树莓派IP地址)
                TARGET_PORT = self.broadcast_port

                # 发送广播消息，创建json字典
                broadcast_data = {
                    "name": self.name,
                    "status": self.status,
                    "rpi_ip": self.rpi_ip,
                    "rpi_port": self.rpi_port,
                    "msg": self.msg,
                    "send_time": int(time.time())
                }
                # 编码为JSON字符串
                final_msg = json.dumps(broadcast_data)
                # 发送UDP广播
                sock.sendto(final_msg.encode(), (TARGET_IP, TARGET_PORT))
                print(f"[BROADCAST] to {TARGET_PORT} '{final_msg}' ")
            except Exception as e:
                print(f"[ERROR] UDP broadcast failed: {e}")
            finally:
                sock.close()

            # 广播间隔
            time.sleep(self.brodcast_interval)

    # 发送 UDP 消息给指定主机
    def send_message(self, message: str):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = {
            "name": self.name,
            "status": self.status,
            "rpi_ip": self.rpi_ip,
            "rpi_port": self.rpi_port,
            "msg": message,
            "send_time": int(time.time())
        }
        try:
            sock.sendto(json.dumps(msg).encode(), (self.target_ip, self.target_port))
            print(f"[SEND] to {self.target_ip}:{self.target_port} '{message}' ")
            # 记录最后发送的信息
            self.msg = message
        except Exception as e:
            print(f"[ERROR] UDP send failed: {e}")
        finally:
            sock.close()

    # 更新状态
    def update_status(self, status: str):
        if status in self.status_dict.values():
            self.status = status
        else:
            print(f"[ERROR] Invalid status: {status}")

    # 处理接收到的命令
    def get_command(self):
        while True:
            try:
                cmd = self.target_listener.queue.get_nowait()  # 非阻塞取命令
                print(f"接收到广播: {cmd}")
            except queue.Empty:
                pass
    





# debug main
if __name__ == "__main__":
    try:

        # 创建 UDP 连接器
        pccon = PCConnector(name="OpenLapse",brodcast_interval=0.5)

        # 再开一个线程用于接收命令
        threading.Thread(target=pccon.get_command, daemon=True).start()

        # 主线程循环
        while True:
            time.sleep(5)
            # print("[INFO] Main thread running...")
            pccon.send_message(time.strftime("%H:%M:%S", time.localtime()))
            # time.sleep(5)
            # pccon.update_status("CONNECTED")
    # ctrl+c 退出
    except KeyboardInterrupt:
        print("\n[INFO] Exiting...")
