#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from datetime import datetime

try:
    import pyrealsense2 as rs
except ImportError:
    print("未找到 pyrealsense2，请先安装：\n  pip install pyrealsense2\n或使用 conda-forge:\n  conda install -c conda-forge pyrealsense2")
    sys.exit(1)


def intrinsics_to_dict(intrin: rs.intrinsics):
    """将 rs.intrinsics 转为可序列化字典"""
    return {
        "width": intrin.width,
        "height": intrin.height,
        "fx": intrin.fx,
        "fy": intrin.fy,
        "cx": intrin.ppx,
        "cy": intrin.ppy,
        "model": str(intrin.model),   # 畸变模型
        "coeffs": list(intrin.coeffs) # 5 个畸变系数
    }


def extrinsics_to_dict(extrin: rs.extrinsics):
    """将 rs.extrinsics 转为可序列化字典"""
    return {
        "rotation_3x3_row_major": list(extrin.rotation),   # 长度9
        "translation_xyz_meters": list(extrin.translation) # 长度3, 单位米
    }


def print_intrinsics(name, intrin_dict):
    print(f"\n[{name}] 内参：")
    print(f"  分辨率: {intrin_dict['width']} x {intrin_dict['height']}")
    print(f"  fx, fy: {intrin_dict['fx']:.6f}, {intrin_dict['fy']:.6f}")
    print(f"  cx, cy: {intrin_dict['cx']:.6f}, {intrin_dict['cy']:.6f}")
    print(f"  畸变模型: {intrin_dict['model']}")
    print(f"  畸变系数(k1,k2,p1,p2,k3): {intrin_dict['coeffs']}")


def main(save_json=True, json_path=None):
    ctx = rs.context()

    if len(ctx.devices) == 0:
        print("未检测到 RealSense 设备。请检查连接。")
        sys.exit(1)

    dev = ctx.devices[0]
    serial = dev.get_info(rs.camera_info.serial_number)
    name = dev.get_info(rs.camera_info.name)
    print(f"检测到设备：{name} (S/N: {serial})")

    # 配置并启动 pipeline
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_device(serial)

    # 尝试同时启用彩色与深度（若某一路不存在，RealSense SDK 会选择可用的）
    # 你也可以显式指定分辨率/帧率
    try:
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    except Exception:
        pass

    try:
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    except Exception:
        pass

    profile = pipeline.start(config)

    # 获取活动 profile 下的流配置
    color_profile = None
    depth_profile = None

    for s in profile.get_streams():
        sp = s.as_video_stream_profile()
        if s.stream_type() == rs.stream.color:
            color_profile = sp
        if s.stream_type() == rs.stream.depth:
            depth_profile = sp

    result = {
        "device": {
            "name": name,
            "serial_number": serial
        },
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "streams": {}
    }

    # 彩色内参
    if color_profile is not None:
        color_intrin = color_profile.get_intrinsics()
        color_intrin_dict = intrinsics_to_dict(color_intrin)
        result["streams"]["color"] = color_intrin_dict
        print_intrinsics("Color", color_intrin_dict)
    else:
        print("\n未启用或未检测到彩色流（color）。")

    # 深度内参
    if depth_profile is not None:
        depth_intrin = depth_profile.get_intrinsics()
        depth_intrin_dict = intrinsics_to_dict(depth_intrin)
        result["streams"]["depth"] = depth_intrin_dict
        print_intrinsics("Depth", depth_intrin_dict)
    else:
        print("\n未启用或未检测到深度流（depth）。")

    # 彩色-深度外参（从 depth 到 color 的变换）
    if color_profile is not None and depth_profile is not None:
        extrin_d2c = depth_profile.get_extrinsics_to(color_profile)
        extrin_c2d = color_profile.get_extrinsics_to(depth_profile)
        d2c_dict = extrinsics_to_dict(extrin_d2c)
        c2d_dict = extrinsics_to_dict(extrin_c2d)
        result["extrinsics"] = {
            "depth_to_color": d2c_dict,
            "color_to_depth": c2d_dict
        }

        print("\n[Extrinsics] 深度坐标系 → 彩色坐标系：")
        print(f"  R(行优先): {d2c_dict['rotation_3x3_row_major']}")
        print(f"  t(米):      {d2c_dict['translation_xyz_meters']}")

    # 可选：保存为 JSON
    if save_json:
        if json_path is None:
            json_path = f"realsense_intrinsics_{serial}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n已保存到：{json_path}")

    # 停止 pipeline
    pipeline.stop()


if __name__ == "__main__":
    # 你也可以通过命令行参数自定义是否保存或保存路径
    # 这里简单调用
    main(save_json=True)
