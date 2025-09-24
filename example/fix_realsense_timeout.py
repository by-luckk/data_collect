#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复RealSense超时问题的脚本
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import os
import time

def fix_realsense_recording():
    """
    修复RealSense录制超时问题
    """
    # 创建输出目录
    root_dir = "debug/funny"
    topic = "fans"
    rgb_dir = os.path.join(root_dir, topic, "rgb")
    depth_dir = os.path.join(root_dir, topic, "depth")
    os.makedirs(rgb_dir, exist_ok=True)
    os.makedirs(depth_dir, exist_ok=True)

    # 创建pipeline
    pipeline = rs.pipeline()
    config = rs.config()

    try:
        # 检查设备可用性
        print("🔍 检查RealSense设备...")
        ctx = rs.context()
        devices = ctx.query_devices()
        if len(devices) == 0:
            print("❌ 没有找到RealSense设备！")
            return False
        
        device = devices[0]
        print(f"✅ 找到设备: {device.get_info(rs.camera_info.name)}")
        print(f"   序列号: {device.get_info(rs.camera_info.serial_number)}")
        
        # 检查是否有其他进程占用相机
        print("🔍 检查设备状态...")
        
        # 配置流 - 使用更保守的设置
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        
        # 启动pipeline
        print("🚀 启动pipeline...")
        profile = pipeline.start(config)
        
        # 重要：给相机预热时间
        print("🔥 相机预热中...")
        warm_up_frames = 30
        for i in range(warm_up_frames):
            try:
                frames = pipeline.wait_for_frames(timeout_ms=10000)  # 增加超时时间
                print(f"   预热帧 {i+1}/{warm_up_frames}")
            except RuntimeError as e:
                print(f"   预热帧 {i+1} 失败: {e}")
                if i < 10:  # 前10帧失败可以容忍
                    continue
                else:
                    raise e
        
        print("✅ 相机预热完成!")
        
        # 获取相机内参
        profile_color = profile.get_stream(rs.stream.color)
        intr_color = profile_color.as_video_stream_profile().get_intrinsics()
        print(f"📷 彩色相机内参: {intr_color}")
        
        # 获取深度scale
        depth_sensor = profile.get_device().first_depth_sensor()
        depth_scale = depth_sensor.get_depth_scale()
        print(f"📏 深度scale: {depth_scale}")
        
        # 创建对齐对象
        align_to = rs.stream.color
        align = rs.align(align_to)
        
        save_count = 0
        frame_count = 0
        
        print("🎬 开始录制...")
        
        while True:
            try:
                # 增加超时时间并添加重试机制
                frames = pipeline.wait_for_frames(timeout_ms=5000)
                
                # 对齐帧
                aligned_frames = align.process(frames)
                aligned_depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()
                
                if not aligned_depth_frame or not color_frame:
                    print("⚠️  帧无效，跳过...")
                    continue
                
                # 转换为numpy数组
                depth_image = np.asanyarray(aligned_depth_frame.get_data())
                color_image = np.asanyarray(color_frame.get_data())
                
                # 保存图像（跳过前30帧）
                if frame_count > 30 and frame_count % 1 == 0:
                    save_count += 1
                    rgb_filename = os.path.join(rgb_dir, f"{save_count:06d}.png")
                    depth_filename = os.path.join(depth_dir, f"{save_count:06d}.png")
                    
                    cv2.imwrite(rgb_filename, color_image)
                    cv2.imwrite(depth_filename, depth_image)
                    
                    if save_count % 30 == 0:  # 每30帧打印一次
                        print(f"📸 已保存 {save_count} 帧")
                
                # 显示预览
                depth_colormap = cv2.applyColorMap(
                    cv2.convertScaleAbs(depth_image, alpha=0.03), 
                    cv2.COLORMAP_JET
                )
                combined_image = cv2.hconcat([color_image, depth_colormap])
                
                # 调整显示大小
                display_image = cv2.resize(combined_image, (1280//2, 480//2))
                cv2.imshow('RGB and Depth (按q退出)', display_image)
                
                frame_count += 1
                
                # 检查退出条件
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("👋 用户退出")
                    break
                    
            except RuntimeError as e:
                print(f"❌ 获取帧失败: {e}")
                print("🔄 尝试重新连接...")
                
                # 重启pipeline
                pipeline.stop()
                time.sleep(1)
                profile = pipeline.start(config)
                
                # 再次预热
                for _ in range(5):
                    try:
                        pipeline.wait_for_frames(timeout_ms=5000)
                    except:
                        pass
                
                continue
                
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False
        
    finally:
        try:
            pipeline.stop()
            cv2.destroyAllWindows()
            print(f"🎉 录制完成! 共保存 {save_count} 帧")
        except:
            pass
    
    return True

if __name__ == "__main__":
    fix_realsense_recording()

