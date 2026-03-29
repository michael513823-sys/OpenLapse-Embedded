import time
import json
import serial
import subprocess
import os

import threading

from libs.connector import PCConnector
from libs.motor import MotorController
from libs.play_music import PWMPlayer
from libs.cam_ffm import MJPEGStreamController
from libs.light import Light,Row,Row24,Row12,Row6



# 初始化电机
def init_motor():
    print("初始化串口")
    # TMC2209驱动串口
    uart = serial.Serial("/dev/serial0", baudrate=115200, timeout=0)

    Z_DIR = 24
    Z_PULS = 23
    Y_DIR = 22
    Y_PULS = 27
    X_DIR = 17
    X_PULS = 18
    Z_EN = 13
    Y_EN = 6
    X_EN = 5

    # 电机
    x_motor = MotorController(uart, 0x02, dir_pin=X_DIR, pulse_pin=X_PULS, enable_pin=X_EN,reverse_dir=True)
    y_motor = MotorController(uart, 0x01, dir_pin=Y_DIR, pulse_pin=Y_PULS, enable_pin=Y_EN,reverse_dir=True)
    z_motor = MotorController(uart, 0x00, dir_pin=Z_DIR, pulse_pin=Z_PULS, enable_pin=Z_EN,reverse_dir=False,begin_with_reverse=False)



    return x_motor,y_motor,z_motor


    # 播放器
    x_player = PWMPlayer(x_motor)
    y_player = PWMPlayer(y_motor)
    z_player = PWMPlayer(z_motor)

    # 串口初始化成功
    x_player.power_on()
    y_player.power_on()
    z_player.power_on()

# 主程序
def main():

    # 背光
    light = Light()
    light.display('ld')
    light.update_percent(10)
    # 电机
    x_motor,y_motor,z_motor = init_motor()
    light.display('MO')
    light.update_percent(20)
    time.sleep(1)

    # # 播放器
    # x_player = PWMPlayer(x_motor)
    # y_player = PWMPlayer(y_motor)
    # z_player = PWMPlayer(z_motor)
    
    # # 电机初始化成功提示音
    # x_player.power_on()
    # y_player.power_on()
    # z_player.power_on()

    # 连接网络
    pc = PCConnector()
    light.display('NE')
    light.update_percent(40)
    time.sleep(1)

    # 启动摄像头推流
    # cam_controller = MJPEGStreamController(host='0.0.0.0', port=8081, width=1280, height=960, fps=30, show_timestamp=True)
    # cam_controller.start()
    light.display('CA')
    light.update_percent(80)
    time.sleep(1)


    light.update_percent(100)
    # # 播放提示音
    # x_player.network_connected()

    def wait_for_connect():
        while not pc.client_connected():  # 阻塞在这里
            pc.update_status('WAITING')
            print('wait_for_connect()')
            light.display('WT')
            time.sleep(0.5)
        # 如果连接成功
        pc.update_status('CONNECTED')
        # # 提示
        light.display('CN')
        
    def reset_motors():
        # 设置电流
        x_motor.set_current(irun=31, ihold=1, delay=4)
        y_motor.set_current(irun=31, ihold=1, delay=4)
        z_motor.set_current(irun=31, ihold=1, delay=4)

        # 设置细分
        x_motor.set_microsteps(16)
        y_motor.set_microsteps(16)
        z_motor.set_microsteps(256)

        # x_motor.en_spreadcycle(False)
        # y_motor.en_spreadcycle(False)
        # z_motor.en_spreadcycle(False)

        # 使能电机
        x_motor.enable_motor(True)
        y_motor.enable_motor(True)
        z_motor.enable_motor(True)

    

    def update_pos():
        pos = {
            'x':x_motor.position,
            'y':y_motor.position,
            'z':z_motor.position,
            'xy_home':(x_motor.is_homed and y_motor.is_homed),
            'z_home':z_motor.is_homed,
            'focusing':z_motor.is_focusing
        }
        pos_str = json.dumps(pos)
        pc.update_msg(pos_str)


    def run_command(cmd: dict):
        print(f"收到原始命令: {cmd}")

        # 移动命令
        if cmd.get('type')=='MOVE':
            direction = int(cmd.get('direction',''))
            steps = int(cmd.get('steps',''))
            speed = int(cmd.get('speed','5000'))
            axis = cmd.get('axis','')
            steps_coef = 1
            speed_coef = 1

            z_steps_coef = 1
            z_speed_coef = 1

            def limit(cur_pos, req_steps, min_pos, max_pos, direction):
                """
                根据当前位置/方向/请求步数裁剪可执行步数。
                返回值：允许执行的步数（>=0）；0 表示已到限位或无需移动。
                约定：req_steps 为正数；direction: 0=负向，1=正向
                """
                # 保护：负数或0步，都不需要跑
                req_steps = int(req_steps)
                if req_steps <= 0:
                    return 0

                if direction == 0:  # 负向
                    if cur_pos <= min_pos:
                        return 0  # 已在/越过最小限位
                    max_allow = cur_pos - min_pos
                    return min(req_steps, max_allow)

                elif direction == 1:  # 正向
                    if cur_pos >= max_pos:
                        return 0  # 已在/越过最大限位
                    max_allow = max_pos - cur_pos
                    return min(req_steps, max_allow)
                
                return 0
            
            update_pos()

            if axis=='X':
                steps = limit(x_motor.position,steps*steps_coef,0,120000,direction)
                if steps > 0:
                    x_motor.set_microsteps(16)
                    def func():
                        x_motor.run_motor_steps(steps=steps, freq=speed * speed_coef, direction=direction)
                    threading.Thread(target=func, daemon=True).start()
                    update_pos()

            elif axis=='Y':
                steps = limit(y_motor.position,steps*steps_coef,0,56000,direction)
                if steps > 0:
                    y_motor.set_microsteps(16)
                    def func():
                        y_motor.run_motor_steps(steps=steps, freq=speed * speed_coef, direction=direction)
                    threading.Thread(target=func, daemon=True).start()
                    update_pos()

            elif axis=='Z':
                steps = limit(z_motor.position,steps* z_steps_coef,0,58000,direction)
                if steps > 0:
                    z_motor.set_microsteps(256)

                    def func():
                        z_motor.run_motor_steps(steps=steps, freq=speed * z_speed_coef, direction=direction)

                    threading.Thread(target=func, daemon=True).start()
                    
                    while z_motor.is_busy():
                        update_pos()
                    update_pos()

            else:
                pass
        
        # 归位命令
        elif cmd.get('type')=='HOME':
            axis = cmd.get('axis','')
            x_motor.set_microsteps(16)
            y_motor.set_microsteps(16)
            z_motor.set_microsteps(16)

            # 设置电流
            x_motor.set_current(irun=31, ihold=15, delay=4)
            y_motor.set_current(irun=31, ihold=15, delay=4)
            z_motor.set_current(irun=31, ihold=15, delay=4)

            x_motor.enable_motor(True)
            y_motor.enable_motor(True)
            z_motor.enable_motor(True)

            if axis=='XY':
                y_motor.move_to_start(sg_drop=80,min_sg=140)
                update_pos()
                x_motor.move_to_start(sg_drop=80,min_sg=140)
                update_pos()
            elif axis=='Z':
                z_motor.move_to_start(sg_drop=80,min_sg=120,speed=0.6)
                update_pos()
            else:
                pass

        elif cmd.get('type')=='MOVETO':
            # 拿到参数
            x_axis_pos = cmd.get('x','')
            y_axis_pos = cmd.get('y','')
            z_axis_pos = cmd.get('z','')
            speed = int(cmd.get('speed','5000'))
            # light_well = cmd.get('light','')

            speed_coef = 1
            z_speed_coef = 1

            # 设置细分等参数
            reset_motors()
            # # 定义线程
            # t1 = threading.Thread(
            #     target=x_motor.move_to_position, 
            #     args=(x_axis_pos, speed*speed_coef), 
            #     kwargs={'auto_home': False}
            #     )
            # t2 = threading.Thread(
            #     target=y_motor.move_to_position, 
            #     args=(y_axis_pos, speed*speed_coef), 
            #     kwargs={'auto_home': False}
            #     )

            # # 启动线程
            # t1.start()
            # t2.start()

            # # 等待两者都完成
            # t1.join()
            # t2.join()

            # 开灯
            # light.well_96(light_well[0],int(light_well[1:]))
            light.all()
            def func():
                if x_axis_pos is not None:
                    x_motor.move_to_position(x_axis_pos,speed*speed_coef,auto_home=True)
                if y_axis_pos is not None:
                    y_motor.move_to_position(y_axis_pos,speed*speed_coef,auto_home=True)
                if z_axis_pos is not None:
                    z_motor.move_to_position(z_axis_pos,speed*z_speed_coef,auto_home=True)

            # threading.Thread(target=func, daemon=True).start()
            func()
            update_pos()

        elif cmd.get('type')=='FOCUS':
            # 拿到参数
            speed = cmd.get('speed',100)
            from_pos = cmd.get('from',0)
            to_pos = cmd.get('to',0)
            cur_pos = cmd.get('cur',0)

            speed_coef = 1
            z_speed_coef = 1

            # 设置细分等参数
            reset_motors()

            light.all()

            update_pos()
            def move():
                pc.update_status('BUSY')
                # 设定开始对焦标志
                z_motor.is_focusing = True
                # 运动到起点
                z_motor.move_to_position(from_pos,speed*z_speed_coef,auto_home=True)
                # 运动到终点
                z_motor.move_to_position(to_pos,speed*z_speed_coef,auto_home=True)
                # 运动到初始位置
                # z_motor.move_to_position(cur_pos,2000,auto_home=True)
                # 结束对焦
                z_motor.is_focusing = False
                pc.update_status('CONNECTED')
            threading.Thread(target=move, daemon=True).start()
            update_pos()

        elif cmd.get('type')=='LIGHT':
            try:
                c = cmd.get('cmd')
                r = cmd.get('r')
                g = cmd.get('g')
                b = cmd.get('b')
                brightness = cmd.get('brt')
                print(r,g,b,brightness)
                if r is not None and g is not None and b is not None:
                    light.led_panel.set_color_correction(int(r), int(g), int(b))
                if brightness is not None:
                    light.led_panel.set_global_brightness(int(brightness))
            except Exception as e:
                c='close'
                print(e)
            if c =='all':
                # 开灯
                light.all()
            if c =='close':
                light.close()

        else:
            pass


    try:
        while True:
            # 阻塞等待连接
            wait_for_connect()
            # 重设电机
            reset_motors()
            time.sleep(0.1)

            # 进入控制循环
            while pc.client_connected(): # 连接后，阻塞在控制循环中
                # 修改状态
                pc.update_status('CONNECTED')
                update_pos()
                # 接收命令
                cmd = pc.receive()
                # 执行命令
                if cmd:
                    pc.update_status('BUSY')
                    run_command(cmd)
                    pc.update_status('CONNECTED')
                time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("程序终止")
    finally:
        pc.close()
        print("程序已退出")


if __name__ == "__main__":
    main()