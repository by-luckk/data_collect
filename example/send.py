# client.py
import socket
import numpy as np
import time

def generate_mock_data(t):
    """生成随时间变化的虚拟位姿数据"""
    # 模拟平移向量（随时间周期性变化）
    translation = np.array([
        0.1 * np.sin(t),  # X轴正弦波动
        0.05 * t,  # Y轴线性增长
        0.3  # Z轴固定
    ], dtype=np.float32)

    # 模拟欧拉角（随时间线性旋转）
    euler = np.array([
        0,  # 绕X轴旋转（固定）
        0,  # 绕Y轴旋转（固定）
        t % (2 * np.pi)  # 绕Z轴旋转（0~360度循环）
    ], dtype=np.float32)

    return translation, euler

def send_data(host, port):
    """连接到服务器并发送数据"""
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                print(f"Connected to server at {host}:{port}.")

                start_time = time.time()
                while True:
                    # 生成模拟数据
                    t = time.time() - start_time
                    translation, euler = generate_mock_data(t)
                    data = translation.tobytes() + euler.tobytes()

                    # 发送数据到服务端
                    s.sendall(data)
                    print(f"Sent data: t={t:.2f}s, translation={translation}, euler={np.degrees(euler)}°")

                    # 接收服务端返回的位姿数据
                    try:
                        # 接收24字节位姿数据
                        pose_data = s.recv(24)
                        if len(pose_data) == 24:
                            translation_pose = np.frombuffer(pose_data[:12], dtype=np.float32)
                            euler_pose = np.frombuffer(pose_data[12:24], dtype=np.float32)
                            print(f"Received current pose from server: translation={translation_pose}, euler={euler_pose}°")
                        else:
                            print(f"Received incomplete pose data: {len(pose_data)} bytes")
                    except socket.timeout:
                        print("Timeout while waiting for pose data")
                    except Exception as e:
                        print(f"Error receiving pose data: {e}")
                        break

                    # 控制发送频率
                    time.sleep(1)

        except (ConnectionRefusedError, ConnectionResetError):
            print("Connection failed. Retrying in 3 seconds...")
            time.sleep(3)
        except Exception as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    # 配置服务器IP和端口
    SERVER_HOST = '192.168.2.222'  # 替换为服务器的实际IP地址
    SERVER_PORT = 65432
    send_data(SERVER_HOST, SERVER_PORT)