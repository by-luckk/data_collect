#!/usr/bin/env python3
"""
采集并上传RealSense的RGB和深度图像数据到服务器
- 图像尺寸: 640*480
- 端口: 3030
- 协议: TCP
- 功能: 采集对齐的RGB和深度图像，并发送到服务器，接收4*4矩阵作为响应
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import socket
import struct
import json
import time
from datetime import datetime


# 服务器配置
SERVER_IP = "115.190.27.42"
SERVER_PORT = 3030

# 图像配置
WIDTH = 640
HEIGHT = 480
FPS = 30

# 日志文件名
MATRIX_LOG_FILE = "transformation_matrices.txt"


def recvall(sock, n):
    """确保接收n字节数据"""
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            raise RuntimeError("连接中断")
        data.extend(packet)
    return bytes(data)


def save_matrix_to_file(T, timestamp):
    """将4x4矩阵保存到文本文件中"""
    try:
        # 检查文件是否存在以决定是否写入文件头
        file_exists = False
        try:
            with open(MATRIX_LOG_FILE, "r"):
                file_exists = True
        except FileNotFoundError:
            file_exists = False

        with open(MATRIX_LOG_FILE, "a") as f:
            # 如果是新文件，写入文件头
            if not file_exists:
                f.write("RealSense Transformation Matrix Log\n")
                f.write("=" * 50 + "\n\n")
            
            # 写入矩阵信息
            f.write(f"Timestamp: {timestamp}\n")
            f.write("Transformation Matrix:\n")
            for row in T:
                # 修复numpy数组格式化问题
                f.write(" ".join(f"{val:.6f}" for val in row) + "\n")
            f.write("\n")
        print(f"矩阵已保存到 {MATRIX_LOG_FILE}")
    except Exception as e:
        print(f"保存矩阵到文件时出错: {e}")


def send_frame_to_server(rgb_bgr, depth_z16, intrinsics):
    """发送RGB和深度图像到服务器，并接收4x4矩阵响应"""
    # 压缩为PNG格式
    ok_rgb, rgb_buf = cv2.imencode(".png", rgb_bgr)  # BGR排列没关系
    ok_dep, dep_buf = cv2.imencode(".png", depth_z16)  # 必须保持uint16
    if not ok_rgb or not ok_dep:
        raise RuntimeError("PNG编码失败")

    # 构建头部信息
    header = {
        "width": WIDTH,
        "height": HEIGHT,
        "fx": intrinsics.fx,
        "fy": intrinsics.fy,
        "cx": intrinsics.ppx,
        "cy": intrinsics.ppy,
        "rgb_format": "png",
        "depth_format": "png",
        "rgb_size": int(len(rgb_buf)),
        "depth_size": int(len(dep_buf))
    }
    header_bytes = json.dumps(header).encode("utf-8")

    try:
        # 创建TCP连接
        with socket.create_connection((SERVER_IP, SERVER_PORT), timeout=30.0) as s:
            # 发送数据: 4字节头长度 + 头部 + RGB + 深度
            s.sendall(struct.pack(">I", len(header_bytes)))
            s.sendall(header_bytes)
            s.sendall(rgb_buf.tobytes())
            s.sendall(dep_buf.tobytes())

            # 接收响应: 4字节响应长度 + JSON数据
            resp_len = struct.unpack(">I", recvall(s, 4))[0]
            resp_data = recvall(s, resp_len)
            resp = json.loads(resp_data.decode("utf-8"))
            
            return resp
    except Exception as e:
        print(f"与服务器通信时出错: {e}")
        return None


def main():
    """主函数"""
    # 创建RealSense pipeline
    pipeline = rs.pipeline()
    config = rs.config()
    
    # 配置流
    config.enable_stream(rs.stream.depth, WIDTH, HEIGHT, rs.format.z16, FPS)
    config.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, FPS)
    
    try:
        # 启动pipeline
        profile = pipeline.start(config)
        
        # 获取颜色流的内参
        color_profile = profile.get_stream(rs.stream.color)
        intrinsics = color_profile.as_video_stream_profile().get_intrinsics()
        print(f"相机内参: fx={intrinsics.fx}, fy={intrinsics.fy}, cx={intrinsics.ppx}, cy={intrinsics.ppy}")
        
        # 创建对齐对象（将深度对齐到颜色）
        align = rs.align(rs.stream.color)
        
        print("开始采集，按 'c' 键捕获并发送图像，按 'q' 键退出")
        
        while True:
            # 等待并获取帧
            frames = pipeline.wait_for_frames()
            
            # 对齐深度帧到颜色帧
            aligned_frames = align.process(frames)
            
            # 获取对齐后的帧
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()
            
            if not depth_frame or not color_frame:
                print("无法获取完整的帧，跳过当前帧")
                continue
                
            # 转换为numpy数组
            depth_image = np.asanyarray(depth_frame.get_data())      # HxW, uint16
            color_image = np.asanyarray(color_frame.get_data())      # HxWx3, uint8 BGR
            
            # 显示图像
            # 深度图像颜色映射
            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
            
            # 水平拼接RGB和深度图像
            combined_image = cv2.hconcat([color_image, depth_colormap])
            
            # 显示窗口
            cv2.imshow('RGB and Aligned Depth', combined_image)
            
            key = cv2.waitKey(1) & 0xFF
            
            # 按 'c' 键捕获并发送图像
            if key == ord('c'):
                print("捕获图像并发送到服务器...")
                t0 = time.time()
                
                response = send_frame_to_server(color_image, depth_image, intrinsics)
                
                if response:
                    print(f"服务器响应: {response}")
                    if response.get("status") == "ok":
                        # 提取4x4矩阵并处理形状
                        T = np.array(response["T"], dtype=float)
                        print(f"接收到的矩阵形状: {T.shape}")
                        
                        # 如果矩阵形状是(1, 4, 4)，则降维为(4, 4)
                        if T.ndim == 3 and T.shape == (1, 4, 4):
                            T = T.reshape(4, 4)
                            print("矩阵已降维为(4, 4)")
                        elif T.ndim == 2 and T.shape == (4, 4):
                            print("矩阵已经是(4, 4)形状")
                        else:
                            print(f"警告: 矩阵形状 {T.shape} 既不是 (1, 4, 4) 也不是 (4, 4)")
                        
                        print("接收到的4x4矩阵:")
                        print(T)
                        
                        # 保存矩阵到文件
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        save_matrix_to_file(T, timestamp)
                    else:
                        print(f"服务器返回错误: {response.get('message', '未知错误')}")
                else:
                    print("发送图像失败，无响应")
                    
                print(f"通信耗时: {time.time()-t0:.3f}秒")
                
            # 按 'q' 键退出
            elif key == ord('q'):
                break
                
    except rs.error as e:
        print(f"RealSense错误: {e.get_message()}")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        # 停止pipeline并关闭所有窗口
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()