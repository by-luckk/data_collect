#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REALSENSE D400系列相机录制脚本
功能：录制RGB和深度图像序列，用于机械臂视觉系统开发
作者：AI Assistant
日期：2024
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import os
import time
import json
from pathlib import Path
import argparse

class RealSenseRecorder:
    def __init__(self, output_dir="REALSENSE/test1", width=640, height=480, fps=30, align_to: str = "color"):
        """
        初始化RealSense录制器
        
        Args:
            output_dir (str): 输出目录
            width (int): 图像宽度
            height (int): 图像高度
            fps (int): 帧率
            align_to (str): 对齐目标，"color" 或 "depth"
        """
        self.output_dir = Path(output_dir)
        self.width = width
        self.height = height
        self.fps = fps
        
        # 对齐目标：color 或 depth（必须先设置！）
        align_to = align_to.lower()
        if align_to not in ("color", "depth"):
            raise ValueError("align_to 必须为 'color' 或 'depth'")
        self.align_to = align_to
        
        # 创建输出目录
        self.rgb_dir = self.output_dir / "RGB"
        self.depth_dir = self.output_dir / "depth"
        self.rgb_dir.mkdir(parents=True, exist_ok=True)
        self.depth_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化RealSense管道
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        
        # 配置流
        self.config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
        self.config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
        
        # 创建对齐对象
        self.align = rs.align(rs.stream.color if self.align_to == "color" else rs.stream.depth)
        
        # 录制统计
        self.frame_count = 0
        self.start_time = None
        
    def check_and_report_intrinsics(self):
        """
        检查并报告RGB与深度的内参与外参。注意：RealSense双目深度与彩色相机物理上为不同相机，
        内参通常不会完全一致。我们仅要求分辨率一致，并建议按需选择对齐目标：
        - 若以彩色图像做检测/追踪，建议对齐到color并使用彩色相机内参
        - 若以深度度量精度为先，建议对齐到depth并使用深度相机内参

        Returns:
            bool: 分辨率是否匹配（匹配则返回True，否则False）
        """
        try:
            # 启动管道获取内参
            profile = self.pipeline.start(self.config)
            
            # 获取深度和彩色流的内参
            depth_profile = rs.video_stream_profile(profile.get_stream(rs.stream.depth))
            color_profile = rs.video_stream_profile(profile.get_stream(rs.stream.color))
            
            depth_intrinsics = depth_profile.get_intrinsics()
            color_intrinsics = color_profile.get_intrinsics()
            # 获取外参（从深度到彩色）
            depth_to_color_extr = depth_profile.get_extrinsics_to(color_profile)
            color_to_depth_extr = color_profile.get_extrinsics_to(depth_profile)
            
            # 检查分辨率
            if (depth_intrinsics.width != color_intrinsics.width or 
                depth_intrinsics.height != color_intrinsics.height):
                print(f"❌ 分辨率不匹配:")
                print(f"   深度: {depth_intrinsics.width}x{depth_intrinsics.height}")
                print(f"   彩色: {color_intrinsics.width}x{color_intrinsics.height}")
                return False
            
            print("🔍 相机内外参：")
            print(f"   深度相机内参: fx={depth_intrinsics.fx:.2f}, fy={depth_intrinsics.fy:.2f}")
            print(f"                 cx={depth_intrinsics.ppx:.2f}, cy={depth_intrinsics.ppy:.2f}")
            print(f"   彩色相机内参: fx={color_intrinsics.fx:.2f}, fy={color_intrinsics.fy:.2f}")
            print(f"                 cx={color_intrinsics.ppx:.2f}, cy={color_intrinsics.ppy:.2f}")
            print("   外参（深度->彩色）:")
            print(f"     rotation(3x3): {list(depth_to_color_extr.rotation)}")
            print(f"     translation(3): {list(depth_to_color_extr.translation)}")
            print(f"   外参（彩色->深度）:")
            print(f"     rotation(3x3): {list(color_to_depth_extr.rotation)}")
            print(f"     translation(3): {list(color_to_depth_extr.translation)}")
            print(f"✅ 分辨率匹配，已选择对齐到: {self.align_to}")
            
            # 保存内参信息
            intrinsics_data = {
                "depth_intrinsics": {
                    "width": depth_intrinsics.width,
                    "height": depth_intrinsics.height,
                    "fx": depth_intrinsics.fx,
                    "fy": depth_intrinsics.fy,
                    "ppx": depth_intrinsics.ppx,
                    "ppy": depth_intrinsics.ppy,
                    "coeffs": depth_intrinsics.coeffs
                },
                "color_intrinsics": {
                    "width": color_intrinsics.width,
                    "height": color_intrinsics.height,
                    "fx": color_intrinsics.fx,
                    "fy": color_intrinsics.fy,
                    "ppx": color_intrinsics.ppx,
                    "ppy": color_intrinsics.ppy,
                    "coeffs": color_intrinsics.coeffs
                },
                "extrinsics": {
                    "depth_to_color": {
                        "rotation": list(depth_to_color_extr.rotation),
                        "translation": list(depth_to_color_extr.translation)
                    },
                    "color_to_depth": {
                        "rotation": list(color_to_depth_extr.rotation),
                        "translation": list(color_to_depth_extr.translation)
                    }
                },
                "align_to": self.align_to
            }
            
            with open(self.output_dir / "intrinsics.json", "w") as f:
                json.dump(intrinsics_data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"❌ 检查内参时出错: {e}")
            return False
        finally:
            # 停止管道以便重新启动
            try:
                self.pipeline.stop()
            except:
                pass
    
    def start_recording(self, duration=None, max_frames=None):
        """
        开始录制
        
        Args:
            duration (float): 录制时长（秒），None表示手动停止
            max_frames (int): 最大帧数，None表示无限制
        """
        print(f"🎬 开始录制到目录: {self.output_dir}")
        print(f"   分辨率: {self.width}x{self.height}")
        print(f"   帧率: {self.fps} FPS")
        print(f"   对齐目标: {self.align_to}")
        
        if duration:
            print(f"   录制时长: {duration} 秒")
        if max_frames:
            print(f"   最大帧数: {max_frames}")
        
        print("   按 'q' 键或 Ctrl+C 停止录制")
        
        try:
            # 启动管道
            profile = self.pipeline.start(self.config)
            
            # 等待相机稳定
            print("📷 等待相机稳定...")
            for _ in range(30):
                self.pipeline.wait_for_frames()
            
            self.start_time = time.time()
            
            print("🔴 开始录制...")
            
            while True:
                # 检查停止条件
                if duration and (time.time() - self.start_time) > duration:
                    print(f"⏰ 达到录制时长 {duration} 秒，停止录制")
                    break
                
                if max_frames and self.frame_count >= max_frames:
                    print(f"📸 达到最大帧数 {max_frames}，停止录制")
                    break
                
                # 获取帧
                frames = self.pipeline.wait_for_frames()
                
                # 对齐深度和彩色帧
                aligned_frames = self.align.process(frames)
                
                # 获取对齐后的帧
                depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()
                
                if not depth_frame or not color_frame:
                    continue
                
                # 转换为numpy数组
                depth_image = np.asanyarray(depth_frame.get_data())
                color_image = np.asanyarray(color_frame.get_data())
                
                # 保存图像
                self.save_frame(color_image, depth_image)
                
                # 显示预览（可选）
                self.show_preview(color_image, depth_image)
                
                # 检查退出条件
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("👋 用户按 'q' 键，停止录制")
                    break
                
                self.frame_count += 1
                
                # 每100帧显示进度
                if self.frame_count % 100 == 0:
                    elapsed = time.time() - self.start_time
                    fps_actual = self.frame_count / elapsed
                    print(f"📊 已录制 {self.frame_count} 帧，实际帧率: {fps_actual:.1f} FPS")
                    
        except KeyboardInterrupt:
            print("⏹️ 用户中断，停止录制")
        except Exception as e:
            print(f"❌ 录制过程中出错: {e}")
        finally:
            self.cleanup()
    
    def save_frame(self, color_image, depth_image):
        """
        保存单帧图像
        
        Args:
            color_image (np.array): 彩色图像
            depth_image (np.array): 深度图像
        """
        frame_filename = f"frame_{self.frame_count:06d}.png"
        
        # 保存RGB图像
        rgb_path = self.rgb_dir / frame_filename
        cv2.imwrite(str(rgb_path), color_image)
        
        # 保存深度图像（16位）
        depth_path = self.depth_dir / frame_filename
        cv2.imwrite(str(depth_path), depth_image)
    
    def show_preview(self, color_image, depth_image):
        """
        显示预览窗口
        
        Args:
            color_image (np.array): 彩色图像
            depth_image (np.array): 深度图像
        """
        # 深度图像可视化（映射到0-255范围）
        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(depth_image, alpha=0.03), 
            cv2.COLORMAP_JET
        )
        
        # 水平拼接显示
        combined = np.hstack((color_image, depth_colormap))
        
        # 调整显示大小
        combined = cv2.resize(combined, (combined.shape[1]//2, combined.shape[0]//2))
        
        # 添加文字信息
        cv2.putText(combined, f"Frame: {self.frame_count}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow('RealSense Recording (RGB | Depth)', combined)
    
    def cleanup(self):
        """
        清理资源
        """
        try:
            self.pipeline.stop()
            cv2.destroyAllWindows()
            
            # 生成录制总结
            if self.start_time:
                elapsed = time.time() - self.start_time
                fps_actual = self.frame_count / elapsed if elapsed > 0 else 0
                
                summary = {
                    "recording_info": {
                        "total_frames": self.frame_count,
                        "duration_seconds": elapsed,
                        "average_fps": fps_actual,
                        "target_fps": self.fps,
                        "resolution": f"{self.width}x{self.height}",
                        "output_directory": str(self.output_dir),
                        "rgb_directory": str(self.rgb_dir),
                        "depth_directory": str(self.depth_dir)
                    }
                }
                
                with open(self.output_dir / "recording_summary.json", "w") as f:
                    json.dump(summary, f, indent=2)
                
                print("📋 录制完成!")
                print(f"   总帧数: {self.frame_count}")
                print(f"   录制时长: {elapsed:.1f} 秒")
                print(f"   平均帧率: {fps_actual:.1f} FPS")
                print(f"   RGB图像保存在: {self.rgb_dir}")
                print(f"   深度图像保存在: {self.depth_dir}")
                
        except Exception as e:
            print(f"❌ 清理时出错: {e}")


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='RealSense相机录制脚本')
    parser.add_argument('--output', '-o', default='REALSENSE/test1', 
                       help='输出目录 (默认: REALSENSE/test1)')
    parser.add_argument('--width', '-w', type=int, default=640, 
                       help='图像宽度 (默认: 640)')
    parser.add_argument('--height', '-H', type=int, default=480, 
                       help='图像高度 (默认: 480)')
    parser.add_argument('--fps', '-f', type=int, default=30, 
                       help='帧率 (默认: 30)')
    parser.add_argument('--duration', '-d', type=float, 
                       help='录制时长(秒), 不指定则手动停止')
    parser.add_argument('--max-frames', '-m', type=int, 
                       help='最大帧数, 不指定则无限制')
    parser.add_argument('--align-to', '-a', type=str, default='color', choices=['color','depth'],
                       help='对齐目标: color 或 depth (默认: color)')
    
    args = parser.parse_args()
    
    # 创建录制器
    recorder = RealSenseRecorder(
        output_dir=args.output,
        width=args.width,
        height=args.height,
        fps=args.fps,
        align_to=args.align_to
    )
    
    try:
        # 检查内参一致性
        print("🔍 检查并记录相机内外参...")
        if not recorder.check_and_report_intrinsics():
            print("❌ 分辨率不一致，请在相机驱动中将RGB与深度设置为相同分辨率")
            return
        
        # 开始录制
        recorder.start_recording(
            duration=args.duration,
            max_frames=args.max_frames
        )
        
    except Exception as e:
        print(f"❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
