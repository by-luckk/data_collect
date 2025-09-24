import os
import numpy as np
import pyrealsense2 as rs
import cv2

def rgbd_to_pointcloud(depth, rgb, intr):
    """
    depth  : HxW uint16 (毫米)
    rgb    : HxWx3 uint8
    intr   : rs.intrinsics
    return : (N,6) float32  (x,y,z,r,g,b)  单位米
    """
    h, w = depth.shape
    i, j = np.indices((h, w))
    z = depth.astype(np.float32) / 1000.0                # mm -> m
    x = (j - intr.ppx) / intr.fx * z
    y = (i - intr.ppy) / intr.fy * z

    xyz = np.stack((x, y, z), axis=-1).reshape(-1, 3)    # (N,3)
    rgb_flat = rgb.reshape(-1, 3).astype(np.float32)     # (N,3)
    pc = np.hstack((xyz, rgb_flat))                      # (N,6)
    pc = pc[pc[:,2] > 0]                                 # 去掉无效深度
    return pc

def save_ply(fname, pc):
    """
    pc : (N,6) float32  x y z r g b
    """
    n = pc.shape[0]
    header = (f"ply\nformat ascii 1.0\nelement vertex {n}\n"
              "property float x\nproperty float y\nproperty float z\n"
              "property uchar red\nproperty uchar green\nproperty uchar blue\n"
              "end_header\n")
    with open(fname, "w") as f:
        f.write(header)
        for x, y, z, r, g, b in pc:
            f.write(f"{x:.6f} {y:.6f} {z:.6f} {int(r)} {int(g)} {int(b)}\n")

def main(out_npy="one_frame.npy", out_ply="one_frame.ply"):
    # ---------- RealSense 初始化 ----------
    pipeline = rs.pipeline()
    cfg = rs.config()
    cfg.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    cfg.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    profile = pipeline.start(cfg)

    # 对齐到彩色
    align = rs.align(rs.stream.color)

    print("[INFO] 等待第一帧 …")
    frames = pipeline.wait_for_frames()
    aligned = align.process(frames)
    color_frame = aligned.get_color_frame()
    depth_frame = aligned.get_depth_frame()

    if not depth_frame or not color_frame:
        print("[ERR] 获取帧失败")
        return

    # ---------- 转 numpy ----------
    depth = np.asanyarray(depth_frame.get_data())
    color = np.asanyarray(color_frame.get_data())

    # ---------- 生成点云 ----------
    intr = color_frame.profile.as_video_stream_profile().intrinsics
    pc = rgbd_to_pointcloud(depth, color, intr)          # (N,6) float32

    # ---------- 保存 ----------
    np.save(out_npy, pc)
    save_ply(out_ply, pc.astype(np.float32))
    print(f"[INFO] 保存完成：{out_npy}, {out_ply}  (共 {pc.shape[0]} 点)")

    pipeline.stop()

if __name__ == "__main__":
    main()
