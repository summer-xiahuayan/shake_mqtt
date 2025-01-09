import time
import keyboard
import numpy as np
import yaml
import socket
import paho.mqtt.client as mqtt
import queue
import threading
from collections import deque
import json
import os

def load_config(config_path) -> dict:
    # Load config
    with open(config_path, 'r',encoding='utf-8') as stream:
        current_config = yaml.load(stream, Loader=yaml.Loader)
    return current_config

def get_voltage(byte_):
    byte_list=list(byte_)
    byte_list.reverse()
    byte_list=byte_list[:-1]
    # 转换为整数，去掉最高符号位
    value = int.from_bytes(byte_list, byteorder='big') & 0x7FFFFF
    sign=(int.from_bytes(byte_list, byteorder='big') & 0x800000)>>23
    # 计算电压
    max_value = 8388607  # 2^23 - 1
    if sign==1:
        value=value-max_value
    voltage = value * 10.0 / max_value * 1000  # 转换为毫伏
    return voltage


def pack_order(config):
    # 解析配置
    iepe_v=config['iepe_v']
    gain = config['gain']
    channel = config['channel']
    sps = config['sps']
    for i,x in enumerate(gain):
        if x==0:
            gain[i]=0x00
        elif x==1:
            gain[i]=0x01
        elif x==2:
            gain[i]=0x02
        else:
            gain[i]=0x03

    iepe_v_=[0x00 if x==0 else 0x01 for x in iepe_v]
    for i,y in enumerate(iepe_v):
        if y==0:
            iepe_v_[i]=0x00
        elif y==1:
            iepe_v_[i]=0x01
        elif y==2:
            iepe_v_[i]=0x02
        elif y==3:
            iepe_v_[i]=0x03
        elif y==4:
            iepe_v_[i]=0x04
        elif y==5:
            iepe_v_[i]=0x05
        elif y==6:
            iepe_v_[i]=0x06
        elif y==7:
            iepe_v_[i]=0x07
        elif y==8:
            iepe_v_[i]=0x08
        elif y==9:
            iepe_v_[i]=0x09
        elif y==10:
            iepe_v_[i]=0x0A
        else:
            iepe_v_[i]=0x00


    iepe_v_command=[0x1B,0x00]+iepe_v_+[0x0D,0x0A]
    gain_command = [0x19, 0x00] + gain+[0x0D,0x0A]
    # 生成采样频率及通道数量设置命令
    channel_mask_low = sum(1 << i for i, ch in enumerate(channel[:8]) if ch == 1)
    channel_mask_high = sum(1 << (i - 8) for i, ch in enumerate(channel[8:], start=8) if ch == 1)
    sps_low = sps & 0xFF
    sps_high = (sps >> 8) & 0xFF
    sample_command = [0xA1, 0x00, channel_mask_low, channel_mask_high, 0x00,0x01, sps_low, sps_high]+10*[0x00]+[0x0D,0x0A]
    # 生成停止采集命令
    stop_command = [0x38,0x00] + [0x00] * 16+[0x0D,0x0A]
    # 将命令转换为字符串形式
    iepe_v_command_str=' '.join(f'{b:02X}' for b in iepe_v_command)
    gain_command_str = ' '.join(f'{b:02X}' for b in gain_command)
    sample_command_str = ' '.join(f'{b:02X}' for b in sample_command)
    stop_command_str = ' '.join(f'{b:02X}' for b in stop_command)

    return bytes(iepe_v_command),bytes(gain_command), bytes(sample_command), bytes(stop_command)




# MQTT客户端回调函数

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("连接到MQTT服务器成功")
    else:
        print(f"连接到MQTT服务器失败，返回码: {rc}")

def on_publish(client, userdata, mid):
    if mid%1000==0:
        print(f"消息已发布，消息ID: {mid}")

# 发送数据的线程函数

def send_data(config=None):
    try:
        print("时域发送数据线程开始")
        sps = config['sps']
        sps=1.01*sps
        channel=config['channel']
        channels=[]
        for i,x in enumerate(channel):
            if x!=0:
                channels.append(i+1)
        while True:
            # 从队列中获取消息
            # if mqtt_queue.qsize()!=0:
            #     message = mqtt_queue.get()
            #     # 发送消息到MQTT主题
            #     for i,x in enumerate(message):
            #         client.publish(mqtt_topic+'_ch'+str(channels[i]), x)
            #     print(f"发送消息: {message} 到主题: {mqtt_topic}")
            #     # 模拟等待
            #     time.sleep(1/sps)
            message_array = np.array(mqtt_deque)
            # 发送消息到MQTT主题
            for i,x in enumerate(channels):
                data = {
                    "voltage": message_array[:,i].tolist()
                }
                data_json=json.dumps(data)
                client.publish(mqtt_topic+'_ch'+str(channels[i]),data_json)
           # print(f"发送消息: {message_array} 到主题: {mqtt_topic}")
            # 模拟等待
            time.sleep(1/sps)
    except KeyboardInterrupt:
        print("时域发送数据线程终止")


def fft(config):
    try:
        print("频域发送数据线程开始")
        fft_refresh_fre=config['fft_refresh_fre']
        sps=config['sps']
        fft_window=config['fft_window']
        channel=config['channel']
        channels=[]
        for i,x in enumerate(channel):
            if x!=0:
                channels.append(i+1)
        while True:
            fft_window_array=np.array(fft_window_deque)
            for i,x in enumerate(channels):
                fft_result = np.fft.fft(fft_window_array[:,i], n=fft_window)
                fft_magnitude = np.abs(fft_result)  # 取模（幅度）
                fft_frequency = np.fft.fftfreq(fft_window, d=1/sps)  # 计算频率轴
                fft_magnitude_list = fft_magnitude.tolist()
                fft_frequency_list = fft_frequency.tolist()
                fft_data = {
                    "magnitude": fft_magnitude_list,
                    "frequency": fft_frequency_list
                }
                # 将字典转换为JSON字符串
                fft_json = json.dumps(fft_data)
                client.publish(mqtt_topic+'_ch'+str(channels[i])+'_fft',fft_json)
                time.sleep(1/fft_refresh_fre)
    except KeyboardInterrupt:
        print("频域发送数据线程终止")

# 定义断开连接的函数
def disconnect_socket(client_socket):

    print("按下按键，断开连接")
    client_socket.close()
    client.disconnect()
    client.loop_stop()
    print("连接已断开")
    # 退出程序
    exit()








def start_tcp_server(config):
    server_ip=config['server_ip']
    server_port=config['server_port']
    # 创建TCP套接字
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 绑定IP地址和端口
    server_socket.bind((server_ip, server_port))
    # 开始监听，参数表示最大连接数
    server_socket.listen(5)
    channels=sum(config['channel'])
    sps = config['sps']

    print(f"服务器正在 {server_ip}:{server_port} 上监听...")
    try:
        iepe_v_command,gain_command, sample_command, stop_command=pack_order(config)
        while True:
            # 等待客户端连接
            client_socket, client_address = server_socket.accept()
            print(f"客户端 {client_address} 已连接")
            try:
                time.sleep(0.5)
                print("设置输入模式")
                client_socket.sendall(iepe_v_command)
                time.sleep(0.5)
                print("设置通道增益")
                client_socket.sendall(gain_command)
                time.sleep(0.5)
                print("发送采集开始命令")
                client_socket.sendall(sample_command)
                # 接收数据
                while True:
                    data = client_socket.recv(channels*4)
                    voltage=[]
                    if not data:
                        break  # 如果没有数据，跳出循环
                    for i in range(0,len(data),4):
                        voltage.append(get_voltage(data))
                   # mqtt_queue.put(voltage)
                    mqtt_deque.append(voltage)
                    fft_window_deque.append(voltage)
                    #print(f"收到数据: {voltage}")
                    time.sleep(1/sps)
            finally:
                # 关闭客户端套接字
                client_socket.close()
                print(f"客户端 {client_address} 连接已关闭")
    except KeyboardInterrupt:
        print("服务器正在关闭...")
    finally:
        # 关闭服务器套接字
        server_socket.close()
        print("服务器已关闭")







if __name__ == "__main__":
    # 获取当前脚本的绝对路径
    script_path = os.path.abspath(__file__)
    # 获取脚本所在的目录
    script_dir = os.path.dirname(script_path)
    # 构建配置文件的路径
    config_file_path = os.path.join(script_dir, "config.yaml")
    mqtt_queue=queue.Queue()
    #config_file_path="./config.yaml"
    config=load_config(config_file_path)
    fft_window=config['fft_window']
    mqtt_deque=deque(maxlen=fft_window)
    fft_window_deque=deque(maxlen=fft_window)
    channel=sum(config['channel'])
    for _ in range(fft_window):
        fft_window_deque.append([0.0 for _ in range(channel)])
        mqtt_deque.append([0.0 for _ in range(channel)])
    fft_queue=queue.Queue()
    # 创建MQTT客户端
    client = mqtt.Client()
    # 设置回调函数
    client.on_connect = on_connect
    client.on_publish = on_publish
    mqtt_ip=config['mqtt_ip']
    mqtt_port=config['mqtt_port']
    mqtt_topic=config['mqtt_topic']
    # 连接到MQTT服务器
    client.connect(mqtt_ip, mqtt_port, 60)
    # 启动网络循环
    client.loop_start()
    # 创建并启动发送数据的线程
    send_thread = threading.Thread(target=send_data,kwargs={
        'config': config
    })
    send_thread.start()

    fft_send_thread = threading.Thread(target=fft,kwargs={
        'config': config
    })
    fft_send_thread.start()



    start_tcp_server(config)
    # byte_data1 = bytes([0x84, 0xA0, 0xD4, 0xFF])
    #
    # voltage1 = get_voltage(byte_data1)
    #
    # print(f"示例1电压: {voltage1:.6f} mv")  # 输出: -13.235809 mv

