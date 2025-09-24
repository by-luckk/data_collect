#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyrealsense2 as rs
import numpy as np
import cv2
import os, json
from datetime import datetime

# -------- 参数 --------
root_dir = "debug/funny"
topic = "fans"
mode = "save"           # "save" / "nosave"
W, H = 640, 480
TARGET_FPS = 10         # 尝试 10，不支持则退到 15 或 30
PRINT_EXTRINSICS = True
# ----------------------

rgb_dir   = os.path.join(root_dir, topic, "rgb")
depth_dir = os.path.join(root_dir, topic, "depth")
os.makedirs(rgb_dir, exist_ok=True)
os.makedirs(depth_dir, exist_ok=True)

def pick_best_profiles(device, w, h, target_fps):
    """从设备可用profile里，挑一组 depth 和 color 的640x480，fps优先靠近target_fps。
       color 格式优先: BGR8 > RGB8 > YUYV > MJPG"""
    def fps_rank(avail, target):
        # 选最接近 target 的，若没有就选 15 或 30
        if target in avail: return target
        for f in (15, 30, 6):  # 一些设备有 6 fps
            if f in avail: return f
        return sorted(avail)[-1]

    preferred_color_formats = [rs.format.bgr8, rs.format.rgb8, rs.format.yuyv, rs.format.mjpeg]
    depth_format = rs.format.z16

    color_candidates = []
    depth_candidates = []

    for s in device.sensors:
        for p in s.get_stream_profiles():
            v = p.as_video_stream_profile() if p.is_video_stream_profile() else None
            if v is None: 
                continue
            if v.width() == w and v.height() == h:
                st = v.stream_type()
                fmt = v.format()
                fps = v.fps()
                if st == rs.stream.color and fmt in preferred_color_formats:
                    color_candidates.append((fps, fmt))
                if st == rs.stream.depth and fmt == depth_format:
                    depth_candidates.append((fps, fmt))

    if not color_candidates or not depth_candidates:
        return None, None

    color_fpses = sorted({f for f, _ in color_candidates})
    depth_fpses = sorted({f for f, _ in depth_candidates})

    cfps = fps_rank(color_fpses, target_fps)
    dfps = fps_rank(depth_fpses, target_fps)

    # 颜色优先选更友好的像素格式
    for fmt in preferred_color_formats:
        if (cfps, fmt) in color_candidates:
            color_choice = (cfps, fmt); break
    else:
        # 退而求其次
        color_choice = sorted(color_candidates)[0]

    # 深度只有Z16
    if (dfps, depth_format) in depth_candidates:
        depth_choice = (dfps, depth_format)
    else:
        depth_choice = sorted(depth_candidates)[0]

    return depth_choice, color_choice

def intr_to_dict(intr):
    return {
        "width": intr.width, "height": intr.height,
        "fx": intr.fx, "fy": intr.fy, "cx": intr.ppx, "cy": intr.ppy,
        "model": str(intr.model), "coeffs": list(intr.coeffs)
    }

# 0) 先拿设备对象
ctx = rs.context()
if len(ctx.devices) == 0:
    raise RuntimeError("未检测到 RealSense 设备，请检查USB连接/权限（udev规则）")

dev = ctx.devices[0]

# 1) 先挑可用的 profile 组合
depth_sel, color_sel = pick_best_profiles(dev, W, H, TARGET_FPS)
if depth_sel is None or color_sel is None:
    raise RuntimeError("设备不支持 640x480 的 depth/color 组合，请用 realsense-viewer 检查支持的分辨率/帧率/格式")

(dfps, dfmt) = depth_sel
(cfps, cfmt) = color_sel
print(f"将使用分辨率 640x480，color FPS={cfps}，depth FPS={dfps}，color 格式={cfmt}, depth 格式={dfmt}")

# 2) 配置并启动
pipeline = rs.pipeline()
config = rs.config()
# 指定具体设备（避免多机冲突）
serial = dev.get_info(rs.camera_info.serial_number)
config.enable_device(serial)

config.enable_stream(rs.stream.depth, W, H, dfmt, dfps)
config.enable_stream(rs.stream.color, W, H, cfmt, cfps)

# 确保没有其他程序占用（请关闭 realsense-viewer 之类）
profile = pipeline.start(config)

# 3) 打印内参/外参/scale
color_vsp = profile.get_stream(rs.stream.color).as_video_stream_profile()
depth_vsp = profile.get_stream(rs.stream.depth).as_video_stream_profile()

color_info = intr_to_dict(color_vsp.get_intrinsics())
depth_info = intr_to_dict(depth_vsp.get_intrinsics())

print("\n===== Camera Intrinsics =====")
print(f"[Color] {color_info['width']}x{color_info['height']}  fx,fy=({color_info['fx']:.6f},{color_info['fy']:.6f})  "
      f"cx,cy=({color_info['cx']:.6f},{color_info['cy']:.6f})")
print(f"[Depth] {depth_info['width']}x{depth_info['height']}  fx,fy=({depth_info['fx']:.6f},{depth_info['fy']:.6f})  "
      f"cx,cy=({depth_info['cx']:.6f},{depth_info['cy']:.6f})")
print(f"Color 畸变: {color_info['model']} {color_info['coeffs']}")
print(f"Depth 畸变: {depth_info['model']} {depth_info['coeffs']}")

depth_scale = profile.get_device().first_depth_sensor().get_depth_scale()
print("Depth Scale:", depth_scale, "(m/unit)")

R = t = None
if PRINT_EXTRINSICS:
    e = depth_vsp.get_extrinsics_to(color_vsp)
    R, t = list(e.rotation), list(e.translation)
    print("[Extrinsics] Depth -> Color")
    print("  R (row-major):", R)
    print("  t (m):        ", t)

# 保存一次元信息
meta_path = os.path.join(root_dir, topic, "intrinsics_extrinsics.json")
os.makedirs(os.path.dirname(meta_path), exist_ok=True)
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "resolution": [W, H],
        "fps": {"color": cfps, "depth": dfps},
        "depth_scale": depth_scale,
        "intrinsics": {"color": color_info, "depth": depth_info},
        "extrinsics": {"depth_to_color": {"rotation_row_major": R, "translation_m": t}}
    }, f, indent=2, ensure_ascii=False)
print(f"已保存参数到: {meta_path}")

input("\n已打印/保存内参，按回车开始采集（按 S 停止）...")

align = rs.align(rs.stream.color)
save_count = 0

try:
    while True:
        frames = pipeline.wait_for_frames()
        aligned = align.process(frames)
        d = aligned.get_depth_frame()
        c = aligned.get_color_frame()
        if not d or not c:
            continue

        depth_img = np.asanyarray(d.get_data())
        color_img = np.asanyarray(c.get_data())

        if mode == "save":
            save_count += 1
            cv2.imwrite(os.path.join(rgb_dir,   f"{save_count:06d}.png"), color_img)
            cv2.imwrite(os.path.join(depth_dir, f"{save_count:06d}.png"), depth_img)

        depth_vis = cv2.applyColorMap(cv2.convertScaleAbs(depth_img, alpha=0.03), cv2.COLORMAP_JET)
        view = cv2.hconcat([color_img, depth_vis])
        cv2.imshow("RGB | Aligned Depth (press S to stop)", view)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('s'), ord('S')):
            print("按 S，采集结束")
            break
finally:
    cv2.destroyAllWindows()
    pipeline.stop()
