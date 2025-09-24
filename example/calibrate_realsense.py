#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RealSense相机内参标定和修改工具
包含多种标定方法和内参管理功能
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import json
import os
from pathlib import Path
import glob

class RealSenseCalibrator:
    def __init__(self):
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        
    def get_current_intrinsics(self):
        """
        获取当前相机内参
        """
        try:
            # 启动相机
            profile = self.pipeline.start(self.config)
            
            # 获取内参
            color_profile = rs.video_stream_profile(profile.get_stream(rs.stream.color))
            depth_profile = rs.video_stream_profile(profile.get_stream(rs.stream.depth))
            
            color_intrinsics = color_profile.get_intrinsics()
            depth_intrinsics = depth_profile.get_intrinsics()
            
            print("📷 当前相机内参:")
            print(f"彩色相机: fx={color_intrinsics.fx:.2f}, fy={color_intrinsics.fy:.2f}")
            print(f"         cx={color_intrinsics.ppx:.2f}, cy={color_intrinsics.ppy:.2f}")
            print(f"深度相机: fx={depth_intrinsics.fx:.2f}, fy={depth_intrinsics.fy:.2f}")
            print(f"         cx={depth_intrinsics.ppx:.2f}, cy={depth_intrinsics.ppy:.2f}")
            
            return color_intrinsics, depth_intrinsics
            
        finally:
            try:
                self.pipeline.stop()
            except:
                pass
    
    def calibrate_with_chessboard(self, chessboard_size=(9, 6), square_size=0.025):
        """
        使用棋盘格标定相机内参
        
        Args:
            chessboard_size: 棋盘格内角点数量 (宽, 高)
            square_size: 棋盘格方格边长(米)
        """
        print(f"🎯 开始棋盘格标定...")
        print(f"棋盘格规格: {chessboard_size[0]}x{chessboard_size[1]}, 方格大小: {square_size*1000}mm")
        print("请将棋盘格放在相机前，按空格键捕获图像，按q键结束采集")
        
        # 准备物体点
        objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)
        objp *= square_size
        
        # 存储物体点和图像点
        objpoints = []  # 3D点
        imgpoints = []  # 2D点
        
        # 启动相机
        profile = self.pipeline.start(self.config)
        
        try:
            capture_count = 0
            
            while True:
                frames = self.pipeline.wait_for_frames()
                color_frame = frames.get_color_frame()
                
                if not color_frame:
                    continue
                
                # 转换为OpenCV格式
                color_image = np.asanyarray(color_frame.get_data())
                gray = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)
                
                # 查找棋盘格角点
                ret, corners = cv2.findChessboardCorners(gray, chessboard_size, None)
                
                # 显示图像
                display_image = color_image.copy()
                if ret:
                    cv2.drawChessboardCorners(display_image, chessboard_size, corners, ret)
                    cv2.putText(display_image, f"Found! Press SPACE to capture", 
                              (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    cv2.putText(display_image, "Move chessboard to find corners", 
                              (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                cv2.putText(display_image, f"Captured: {capture_count}/20", 
                          (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                cv2.imshow('Calibration', display_image)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord(' ') and ret:
                    # 精细化角点
                    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                    corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                    
                    objpoints.append(objp)
                    imgpoints.append(corners2)
                    capture_count += 1
                    
                    print(f"✅ 捕获第 {capture_count} 张图像")
                    
                    if capture_count >= 20:
                        print("📸 已捕获足够图像，开始标定...")
                        break
                
                elif key == ord('q'):
                    if capture_count < 5:
                        print("❌ 图像数量不足，至少需要5张")
                        continue
                    else:
                        print(f"📸 使用 {capture_count} 张图像进行标定...")
                        break
            
            cv2.destroyAllWindows()
            
            if capture_count < 5:
                print("❌ 标定失败：图像数量不足")
                return None, None
            
            # 执行标定
            print("🔄 正在计算相机内参...")
            h, w = gray.shape[:2]
            ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
                objpoints, imgpoints, (w, h), None, None
            )
            
            if ret:
                print("✅ 标定成功!")
                print(f"重投影误差: {ret:.4f}")
                print("新的相机内参:")
                print(f"fx={camera_matrix[0,0]:.2f}, fy={camera_matrix[1,1]:.2f}")
                print(f"cx={camera_matrix[0,2]:.2f}, cy={camera_matrix[1,2]:.2f}")
                print(f"畸变系数: {dist_coeffs.flatten()}")
                
                # 保存标定结果
                calib_data = {
                    'camera_matrix': camera_matrix.tolist(),
                    'distortion_coefficients': dist_coeffs.tolist(),
                    'reprojection_error': ret,
                    'image_size': [w, h],
                    'chessboard_size': chessboard_size,
                    'square_size': square_size
                }
                
                with open('camera_calibration.json', 'w') as f:
                    json.dump(calib_data, f, indent=2)
                
                print("💾 标定结果已保存到 camera_calibration.json")
                
                return camera_matrix, dist_coeffs
            else:
                print("❌ 标定失败")
                return None, None
                
        finally:
            try:
                self.pipeline.stop()
                cv2.destroyAllWindows()
            except:
                pass
    
    def apply_custom_intrinsics(self, fx, fy, cx, cy):
        """
        应用自定义内参（仅用于测试，不能永久修改硬件）
        """
        print("⚠️  注意：这只是软件层面的参数修改，不会永久改变相机硬件")
        print("如需永久修改，请使用Intel RealSense SDK的官方工具")
        
        # 创建自定义内参对象
        intrinsics = rs.intrinsics()
        intrinsics.width = 640
        intrinsics.height = 480
        intrinsics.fx = fx
        intrinsics.fy = fy
        intrinsics.ppx = cx
        intrinsics.ppy = cy
        intrinsics.model = rs.distortion.brown_conrady
        intrinsics.coeffs = [0, 0, 0, 0, 0]  # 假设无畸变
        
        print(f"✅ 设置新内参: fx={fx}, fy={fy}, cx={cx}, cy={cy}")
        return intrinsics

def show_calibration_methods():
    """
    显示所有可用的标定方法
    """
    print("\n🔧 RealSense相机内参标定方法:")
    print("="*60)
    
    print("\n1️⃣  使用Intel RealSense Viewer（推荐）:")
    print("   - 运行: realsense-viewer")
    print("   - 进入 More -> Calibration")
    print("   - 选择 'On-Chip Calibration' 或 'Tare Calibration'")
    print("   - 按提示完成标定（需要标定目标）")
    
    print("\n2️⃣  使用rs-calibrate工具:")
    print("   - 运行: rs-calibrate")
    print("   - 这是命令行版本的标定工具")
    
    print("\n3️⃣  使用本脚本的OpenCV标定:")
    print("   - 准备9x6的棋盘格标定板")
    print("   - 运行: python calibrate_realsense.py --method opencv")
    
    print("\n4️⃣  手动设置内参（临时）:")
    print("   - 仅用于测试，不会永久保存")
    print("   - 运行: python calibrate_realsense.py --method manual")
    
    print("\n💡 建议流程:")
    print("   1. 首先尝试Intel官方工具（方法1或2）")
    print("   2. 如果需要更精确的标定，使用OpenCV方法")
    print("   3. 对于充电装置应用，建议使用彩色相机内参")
    
    print("\n📋 内参选择建议:")
    print("   - 视觉检测优先：使用彩色相机内参 + align_to='color'")
    print("   - 深度精度优先：使用深度相机内参 + align_to='depth'")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='RealSense相机内参标定工具')
    parser.add_argument('--method', choices=['info', 'opencv', 'manual'], 
                       default='info', help='标定方法')
    parser.add_argument('--fx', type=float, help='手动设置fx')
    parser.add_argument('--fy', type=float, help='手动设置fy') 
    parser.add_argument('--cx', type=float, help='手动设置cx')
    parser.add_argument('--cy', type=float, help='手动设置cy')
    
    args = parser.parse_args()
    
    calibrator = RealSenseCalibrator()
    
    if args.method == 'info':
        show_calibration_methods()
        try:
            calibrator.get_current_intrinsics()
        except Exception as e:
            print(f"❌ 无法获取相机信息: {e}")
    
    elif args.method == 'opencv':
        calibrator.calibrate_with_chessboard()
    
    elif args.method == 'manual':
        if all([args.fx, args.fy, args.cx, args.cy]):
            calibrator.apply_custom_intrinsics(args.fx, args.fy, args.cx, args.cy)
        else:
            print("❌ 手动模式需要提供所有参数: --fx --fy --cx --cy")

if __name__ == "__main__":
    main()
