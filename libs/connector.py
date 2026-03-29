import socket, threading
import time
import json
import queue
import hashlib


def stable_hash(dic: dict) -> str:
    json_str = json.dumps(dic, separators=(',', ':'), sort_keys=True)
    return hashlib.md5(json_str.encode()).hexdigest()

# 广播本机ip和port
class UDPBroadcast:
    def __init__(self, 
                 rpi_name='OpenLapse',
                 broadcast_port=64565, # 广播端口，控制端监听该端口
                 broadcast_interval=0.01
                 ):
        
        # 广播间隔，单位秒
        self.broadcast_interval = broadcast_interval

        self.rpi_ip = self._get_ip()
        self.rpi_port = self._find_free_port()

        self.controller_ip = None
        self.controller_port = None

        self.rpi_name = rpi_name

        # 广播到局域网所有主机
        self.broadcast_ip = '255.255.255.255'  
        self.broadcast_port = broadcast_port

        # 连接成功标志
        self.connected = False

        # 工作参数信息
        self.status_dict = {
            1: "WAITING",    # 等待连接
            2: "CONNECTED",  # 已连接
            3: "BUSY",       # 忙碌中
            4: "ERROR",      # 错误
        }

        self.msg = "waitting for connect"  # 发送的信息
        self.status = "WAITING"  # 当前状态

        # 启动广播
        threading.Thread(target=self._udp_broadcast, daemon=True).start()


    # 查找本地可用端口
    def _find_free_port(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
        return port

    # 查找ip
    def _get_ip(self, timeout=120, interval=1):
        """
        阻塞直到获取到本机真实IP地址（非127.0.0.1）
        timeout: 最长等待时间（秒）
        interval: 每次重试间隔（秒）
        """
        start_time = time.time()
        ip = "0.0.0.0"

        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.settimeout(2)
                    # 不会真正建立连接，只用于确定出口网卡IP
                    s.connect(("8.8.8.8", 80))
                    ip = s.getsockname()[0]
                    if not ip.startswith("0."):
                        return ip
            except OSError:
                pass
            # 每次失败后等待 interval 秒
            time.sleep(interval)

        # 超时后仍未获得有效IP，返回127
        return "127.0.0.1"
    
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
                    "name": self.rpi_name,
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
                # print(f"[BROADCAST] to {TARGET_PORT} '{final_msg}' ")
            except Exception as e:
                print(f"[ERROR] UDP broadcast failed: {e}")
            finally:
                sock.close()

            # 广播间隔
            time.sleep(self.broadcast_interval)


    # 更新状态
    def update_status(self, status: str):
        if status in self.status_dict.values():
            self.status = status
        else:
            print(f"[ERROR] Invalid status: {status}")

    # 更新消息
    def update_msg(self, msg:str):
        self.msg = msg




# TCP服务器端
class TCPServer:
    def __init__(self,
                 reconnect_delay=1.0):

        self.reconnect_delay = reconnect_delay
        self.server = None
        self.conn = None
        self.addr = None
        self.running = False
        self.client_connected = False

        # 启动UDP广播
        self.udpbrc = UDPBroadcast(broadcast_interval=0.5) # type: ignore

        self.host = '0.0.0.0'
        self.port = self.udpbrc.rpi_port



    # ====================================================
    # 启动服务器
    # ====================================================
    def start(self):
        self.running = True
        threading.Thread(target=self._server_loop, daemon=True).start()
        print(f"🚀 TCP服务器启动：监听 {self.host}:{self.port}")

    # ====================================================
    # 主循环：负责监听连接与自动重连
    # ====================================================
    def _server_loop(self):
        """循环监听客户端连接"""
        while self.running:
            if not self.client_connected:
                try:
                    # 启动监听socket
                    if self.server is None:
                        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        self.server.bind((self.host, self.port))
                        self.server.listen(1)
                        self.server.setblocking(False)

                    # 非阻塞accept
                    try:
                        conn, addr = self.server.accept()
                        conn.setblocking(False)
                        self.conn = conn
                        self.addr = addr
                        self.client_connected = True
                        print(f"已连接: {addr}")
                        # threading.Thread(target=self._handle_client, daemon=True).start()
                    except BlockingIOError:
                        time.sleep(0.1)
                        continue

                except Exception as e:
                    print(f"服务器异常: {e}")
                    time.sleep(self.reconnect_delay)
            else:
                time.sleep(0.1)


    # ====================================================
    # 重置连接（等待重连）
    # ====================================================
    def _reset_connection(self):
        """关闭当前连接，等待重连"""
        self.client_connected = False
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        self.conn = None
        self.addr = None
        print("🔁 等待客户端重新连接...")

    # ====================================================
    # 发送消息给客户端
    # ====================================================
    def send(self, msg: str):
        """安全发送消息"""
        if self.client_connected and self.conn:
            try:
                self.conn.sendall(msg.encode())
                return True
            except Exception as e:
                print(f"发送失败: {e}")
                self._reset_connection()
        else:
            print("⚠️ 尚未连接客户端，无法发送")
        return False

    # ====================================================
    # 关闭服务器
    # ====================================================
    def close(self):
        self.running = False
        self.client_connected = False
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        if self.server:
            try:
                self.server.close()
            except:
                pass
        print("TCP服务器已关闭")
    


# 一个应用层的类
class PCConnector:
    def __init__(self):

        # 启动TCP服务器
        self.tcp_server = TCPServer(reconnect_delay=1)
        self.tcp_server.start()
        time.sleep(0.5)  # 等待服务器启动

        # 非阻塞心跳间隔
        self.heartbeat_interval = 2
        threading.Thread(target=self._heartbeat, daemon=True).start()
        
    # 发送消息
    def send(self, type: str, value: str):
        msg_dict = {
            'type':type,
            'value':value
        }
        msg = json.dumps(msg_dict)

        return self.tcp_server.send(msg)

    # 发送心跳包（非阻塞）
    def _heartbeat(self):
        while True:
            if self.tcp_server.client_connected:
                self.send("HEARTBEAT", str(time.time()))
                time.sleep(self.heartbeat_interval)

    # 接收数据
    def receive(self):
        if self.tcp_server.client_connected and self.tcp_server.conn:
            try:
                data = self.tcp_server.conn.recv(1024)
                if data:
                    msg = data.decode(errors='ignore')
                    # print(f"收到消息: {msg}")
                    # 马上返回hash 后的ACK
                    self.send("ACK", stable_hash(json.loads(msg)))
                    # 解析JSON
                    json_data = json.loads(msg)
                    return json_data
                else:
                    time.sleep(0.1)
            except BlockingIOError:
                # time.sleep(0.1)
                # print('receive BlockingIOError')
                pass
            except Exception as e:
                print(f"receive Exception: {e}")
                time.sleep(0.1)
    

    # 关闭连接
    def close(self):
        self.tcp_server.close()

    # 更新UDP状态
    def update_status(self, status: str):
        '''
        "WAITING",    # 等待连接
        "CONNECTED",  # 已连接
        "BUSY",       # 忙碌中
        "ERROR",      # 错误
        '''
        self.tcp_server.udpbrc.update_status(status)
    
    # 更新UDP msg
    def update_msg(self, msg:str):
        self.tcp_server.udpbrc.update_msg(msg)

    # 拿到连接状态
    def client_connected(self):
        if self.tcp_server.client_connected:
            return True
        else:
            return False

# debug main

if __name__ == "__main__":
    c = PCConnector()

    def on_msg(msg):
        print(f"收到消息: {msg}")

    try:
        while True:
            time.sleep(5)
            c.send("MESSAGE", "Hello from Raspberry Pi!")
            c.receive(on_msg)
    except KeyboardInterrupt:
        c.close()
