# server.py
import socket
import numpy as np

# 服务器配置
PORT = 65432  # 服务器端口

def receive_data():
    """接收客户端发送的数据并返回位姿数据"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # 绑定到所有网络接口
        s.bind(('0.0.0.0', PORT))
        s.listen(1)
        print(f"Server is listening on port {PORT}...")

        while True:
            # 等待客户端连接
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")

                while True:
                    try:
                        # 接收客户端发送的数据
                        data = conn.recv(24)  # 12 bytes for translation + 12 bytes for euler angles
                        if not data:
                            break

                        # 解析数据
                        translation = np.frombuffer(data[:12], dtype=np.float32)
                        euler = np.frombuffer(data[12:24], dtype=np.float32)

                        # 打印接收到的数据
                        print(f"Received data: translation={translation}, euler={np.degrees(euler)}°")

                        # 返回当前位姿数据给客户端
                        conn.sendall(data)

                    except Exception as e:
                        print(f"Error: {e}")
                        break


if __name__ == "__main__":
    receive_data()