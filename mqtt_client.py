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



def update(frame,line,point):
    # 这里可以更新fft_result和fft_frequency，或者保持不变
    data=copy.deepcopy(fft_result)
    data.reverse()
    x=[i for i in range(len(data))]
    line.set_ydata(data)
    line.set_xdata(x)

    point.set_offsets(np.c_[0, data[0]])  # 更新点的位置
   # point.set_data(0,data[0])

    ax.relim()  # 重新计算图形的限制

    ax.autoscale()  # 自动调整轴的范围

#print(data)
    return line,point,


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
    line, = ax.plot(np.arange(0,len(fft_result)), fft_result,linewidth=0.8)

    point=ax.scatter([], [], s=10, c='r')  # 使用s=20来设置点的大小

    # 设置轴标签和标题
    ax.set_xlabel('point')
    ax.set_ylabel('Magnitude')
    ax.set_title('Time Domain Plot')
    # # 创建动画
    ani = FuncAnimation(fig, update, frames=np.arange(0, 10000), interval=1000/2048,fargs=(line,point,))
    # 显示图形
    plt.show()



















