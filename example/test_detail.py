import socket, struct, json, time, argparse
import numpy as np, cv2

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
    x = np.linspace(0, 255, WIDTH, dtype=np.uint8)
    rgb = np.stack([np.tile(x, (HEIGHT, 1)),
                    np.flipud(np.tile(x, (HEIGHT, 1))),
                    np.full((HEIGHT, WIDTH), 128, np.uint8)], axis=2)
    depth = np.linspace(500, 1500, WIDTH, dtype=np.uint16)
    depth = np.tile(depth, (HEIGHT, 1))
    return rgb, depth

def send_one_frame(server_ip, server_port, timeout=60.0):
    rgb, depth = build_synthetic_rgbd()
    ok1, rgb_buf = cv2.imencode(".png", rgb)
    ok2, dep_buf = cv2.imencode(".png", depth)
    assert ok1 and ok2

    header = {
        "width": WIDTH, "height": HEIGHT,
        "fx": FX, "fy": FY, "cx": CX, "cy": CY,
        "rgb_format": "png", "depth_format": "png",
        "rgb_size": int(len(rgb_buf)), "depth_size": int(len(dep_buf))
    }
    hbytes = json.dumps(header).encode("utf-8")

    with socket.create_connection((server_ip, server_port), timeout=timeout) as s:
        s.settimeout(timeout)
        print(f"[CLIENT] send header {len(hbytes)} bytes; rgb {len(rgb_buf)}; depth {len(dep_buf)}")
        t0 = time.time()
        s.sendall(struct.pack(">I", len(hbytes)))
        s.sendall(hbytes)
        s.sendall(rgb_buf.tobytes())
        s.sendall(dep_buf.tobytes())
        print(f"[CLIENT] sent payload in {time.time()-t0:.3f}s, waiting response...")

        t1 = time.time()
        resp_len = struct.unpack(">I", recvall(s, 4))[0]
        resp = json.loads(recvall(s, resp_len).decode("utf-8"))
        print(f"[CLIENT] got response in {time.time()-t1:.3f}s, total {time.time()-t0:.3f}s")
        return resp

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=80)
    ap.add_argument("--timeout", type=float, default=60.0)
    args = ap.parse_args()

    resp = send_one_frame(args.server, args.port, args.timeout)
    print("[CLIENT] response head:", {k: resp.get(k) for k in ("status","msg")})
    if resp.get("status") == "ok":
        import numpy as np
        T = np.array(resp["T"], dtype=float)
        print("[CLIENT] T=\n", T)

if __name__ == "__main__":
    main()


#   python test_detail.py --server 115.190.27.42 --port 8888 --timeout 60
