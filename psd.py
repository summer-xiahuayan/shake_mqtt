import copy
import time

import paho.mqtt.client as mqtt
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import json
import threading
# MQTT配置

mqtt_ip = '192.168.230.64'

mqtt_topic = 'shake_ch3'

mqtt_port = 1883



# MQTT客户端回调函数

def on_connect(client, userdata, flags, rc):

    if rc == 0:

        print("连接到MQTT服务器成功")

        # 订阅主题

        client.subscribe(mqtt_topic)

    else:

        print(f"连接到MQTT服务器失败，返回码: {rc}")




def on_message(client, userdata, msg):

    #print(f"收到消息: {msg.payload.decode()} 从主题: {msg.topic}")
    global fft_frequency,fft_result
    fft_data_str=msg.payload.decode()
    fft_data=json.loads(fft_data_str)
    fft_result=fft_data['voltage']
# fft_frequency=fft_data['frequency']
#print(fft_result)





# # 创建图形和轴
# fig, ax = plt.subplots()
# line, = ax.plot(fft_frequency,fft_result)
# # 设置轴标签和标题
# ax.set_xlabel('Frequency (Hz)')
# ax.set_ylabel('Magnitude')
# ax.set_title('Frequency Domain Plot')
# # # 创建动画
# #ani = FuncAnimation(fig, update, frames=np.arange(0, 100), interval=1000)
# # 显示图形
# plt.show()


# 更新函数



def update(frame,line):
    # 这里可以更新fft_result和fft_frequency，或者保持不变
    data=copy.deepcopy(fft_result)
    #data.reverse()
    fft_psd_result = np.fft.fft(data, n=len(data))
    fft_psd_magnitude = np.abs(fft_psd_result)  # 取模（幅度）
    fft_psd_frequency = np.fft.fftfreq(len(data), d=1/2048)  # 计算频率轴
    fft_psd_magnitude=np.fft.fftshift(fft_psd_magnitude)
    fft_psd_frequency=np.fft.fftshift(fft_psd_frequency)
    # 计算功率谱
    fft_power = fft_psd_magnitude ** 2
    # 可选：计算功率谱密度
    frequency_resolution = fft_psd_frequency[1] - fft_psd_frequency[0]
    psd = fft_power / frequency_resolution
    log_psd = 10 * np.log10(psd)
    line.set_ydata(log_psd)
    line.set_xdata(fft_psd_frequency)
    # ax.relim()  # 重新计算图形的限制
    # ax.autoscale()  # 自动调整轴的范围
    #print(data)
    return line,


def plot():
    # 创建MQTT客户端
    client = mqtt.Client()
    # 设置回调函数
    client.on_connect = on_connect
    client.on_message = on_message
    # 连接到MQTT服务器
    client.connect(mqtt_ip, mqtt_port, 60)
    # 启动网络循环，阻塞主线程
    client.loop_forever()



if __name__ == "__main__":

    # 假设这是你的FFT结果和频率轴
    fft_result = [1,2,3]
    fft_frequency = [1,2,3]


    plot_thread = threading.Thread(target=plot)
    plot_thread.start()

    time.sleep(2)


    # 创建图形和轴
    fig, ax = plt.subplots()
    line, = ax.plot(np.arange(0,len(fft_result)), fft_result,linewidth=0.5)

   # point=ax.scatter([], [], s=10, c='r')  # 使用s=20来设置点的大小

    # 设置轴标签和标题
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Magnitude(db)')
    ax.set_title('PSD')
    ax.set_ylim(-40, 80)
    ax.set_xlim(-1000,1000)

# # 创建动画
    ani = FuncAnimation(fig, update, frames=np.arange(0, 10000), interval=1000/2048,fargs=(line,))
    # 显示图形
    plt.show()



















