import socket
import struct
import json
import time
import argparse
import numpy as np
import cv2

# 服务器地址
DEFAULT_IP = "115.190.27.42"   # 先本机自测；部署后改成 115.190.27.42
DEFAULT_PORT = 3333

#    python test_d.py --server 115.190.27.42 --port 3333 --mode synthetic
#    python test_d.py --server 127.0.0.1 --port 3333 --mode synthetic




# 固定内参与分辨率（与你的需求一致）
FX, FY = 607.378, 607.371
CX, CY = 309.53, 248.267
WIDTH, HEIGHT = 640, 480

def recvall(sock, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed")
        buf.extend(chunk)
    return bytes(buf)

def build_synthetic_rgbd():
    """构造 640x480 的对齐 RGB 与 Depth（16UC1），用于纯通信测试。"""
    # RGB：简单的横向渐变 + 网格
    x = np.linspace(0, 255, WIDTH, dtype=np.uint8)
    rgb = np.stack([np.tile(x, (HEIGHT, 1)),
                    np.flipud(np.tile(x, (HEIGHT, 1))),
                    np.full((HEIGHT, WIDTH), 128, np.uint8)], axis=2)
    # 画若干交叉线方便肉眼识别
    for r in range(40, HEIGHT, 80):
        rgb[r-1:r+1, :, :] = 255
    for c in range(40, WIDTH, 80):
        rgb[:, c-1:c+1, :] = 255

    # Depth：以毫米为单位的梯度场（uint16），例如 500~1500 mm
    depth = np.linspace(500, 1500, WIDTH, dtype=np.uint16)
    depth = np.tile(depth, (HEIGHT, 1))
    return rgb, depth

def maybe_get_realsense_frame():
    """可选：从 RealSense 获取对齐后的 RGBD（需要安装 pyrealsense2）。"""
    try:
        import pyrealsense2 as rs
    except Exception:
        return None

    pipeline = rs.pipeline()
    cfg = rs.config()
    cfg.enable_stream(rs.stream.depth, WIDTH, HEIGHT, rs.format.z16, 30)
    cfg.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, 30)
    profile = pipeline.start(cfg)
    align = rs.align(rs.stream.color)

    try:
        for _ in range(30):  # 预热
            frames = pipeline.wait_for_frames()
        frames = pipeline.wait_for_frames()
        aligned = align.process(frames)
        d = aligned.get_depth_frame()
        c = aligned.get_color_frame()
        if not d or not c:
            return None
        depth = np.asanyarray(d.get_data()).astype(np.uint16)   # HxW
        rgb = np.asanyarray(c.get_data())                       # HxWx3, BGR
        if depth.shape != (HEIGHT, WIDTH) or rgb.shape[:2] != (HEIGHT, WIDTH):
            return None
        return rgb, depth
    finally:
        pipeline.stop()

def send_one_frame(server_ip, server_port, rgb_bgr, depth_z16):
    ok_rgb, rgb_buf = cv2.imencode(".png", rgb_bgr)
    ok_dep, dep_buf = cv2.imencode(".png", depth_z16)
    assert ok_rgb and ok_dep, "PNG encode failed"

    header = {
        "width": WIDTH, "height": HEIGHT,
        "fx": FX, "fy": FY, "cx": CX, "cy": CY,
        "rgb_format": "png", "depth_format": "png",
        "rgb_size": int(len(rgb_buf)),
        "depth_size": int(len(dep_buf))
    }
    header_bytes = json.dumps(header).encode("utf-8")

    with socket.create_connection((server_ip, server_port), timeout=5.0) as s:
        s.sendall(struct.pack(">I", len(header_bytes)))
        s.sendall(header_bytes)
        s.sendall(rgb_buf.tobytes())
        s.sendall(dep_buf.tobytes())

        resp_len = struct.unpack(">I", recvall(s, 4))[0]
        resp = json.loads(recvall(s, resp_len).decode("utf-8"))
        return resp

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", type=str, default=DEFAULT_IP)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--mode", choices=["synthetic", "realsense"], default="synthetic",
                    help="synthetic: 人造数据；realsense: 真实相机")
    args = ap.parse_args()

    if args.mode == "realsense":
        frames = maybe_get_realsense_frame()
        if frames is None:
            print("[WARN] RealSense 获取失败，改用 synthetic")
            rgb, depth = build_synthetic_rgbd()
        else:
            rgb, depth = frames
    else:
        rgb, depth = build_synthetic_rgbd()

    t0 = time.time()
    resp = send_one_frame(args.server, args.port, rgb, depth)
    dt = time.time() - t0
    print(f"[CLIENT] round-trip {dt:.3f}s")
    print("[CLIENT] response:", json.dumps(resp)[:400], "...")
    if resp.get("status") == "ok":
        T = np.array(resp["T"], dtype=float)
        print("[CLIENT] T=\n", T)

if __name__ == "__main__":
    main()
