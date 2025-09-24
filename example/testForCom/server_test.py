#!/usr/bin/env python3
import socket, struct, json, threading, argparse, time, sys
from typing import Tuple

def log(msg: str):
    print(msg, flush=True)

def recvall(sock: socket.socket, n: int, label: str) -> bytes:
    """读取固定长度，直到读满或连接断开"""
    buf = bytearray()
    start = time.time()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError(f"socket closed while reading {label} ({len(buf)}/{n})")
        buf.extend(chunk)
    log(f"[SERVER] recv {label}: {n} bytes in {time.time()-start:.3f}s")
    return bytes(buf)

def handle_client(conn: socket.socket, addr: Tuple[str,int], timeout: float):
    conn.settimeout(timeout)
    try:
        log(f"[SERVER] accepted from {addr}")
        # 1) 读 4 字节头长度
        header_len = struct.unpack(">I", recvall(conn, 4, "header_len"))[0]
        # 2) 读 JSON 头
        header = json.loads(recvall(conn, header_len, "header_json").decode("utf-8"))
        w = int(header["width"]); h = int(header["height"])
        fx = float(header["fx"]);  fy = float(header["fy"])
        cx = float(header["cx"]);  cy = float(header["cy"])
        rgb_size   = int(header["rgb_size"])
        depth_size = int(header["depth_size"])
        log(f"[SERVER] header ok: {w}x{h}, K=({fx},{fy},{cx},{cy}), sizes rgb={rgb_size}, depth={depth_size}")

        # 3) 读两段 payload
        _rgb  = recvall(conn, rgb_size,   "rgb_payload")
        _depth= recvall(conn, depth_size, "depth_payload")

        # 4) 回一份演示的 4x4 T
        T = [
            [1.0, 0.0, 0.0, 0.10],
            [0.0, 1.0, 0.0, 0.20],
            [0.0, 0.0, 1.0, 0.30],
            [0.0, 0.0, 0.0, 1.00],
        ]
        resp = {"status":"ok","msg":"pong","server_time":time.time(),"T":T}
        resp_bytes = json.dumps(resp).encode("utf-8")
        conn.sendall(struct.pack(">I", len(resp_bytes)))
        conn.sendall(resp_bytes)
        log(f"[SERVER] responded {len(resp_bytes)} bytes, closing")
    except Exception as e:
        log(f"[SERVER][ERROR] {e}")
        try:
            resp = {"status":"error","msg":str(e)}
            b = json.dumps(resp).encode("utf-8")
            conn.sendall(struct.pack(">I", len(b))); conn.sendall(b)
        except Exception:
            pass
    finally:
        try: conn.close()
        except Exception: pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1", help="仅本机回环测试用，保持 127.0.0.1")
    ap.add_argument("--port", type=int, default=50007)
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()

    log(f"[SERVER] listening on {args.host}:{args.port} (timeout={args.timeout}s)")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((args.host, args.port))
    except OSError as e:
        log(f"[SERVER][FATAL] bind failed: {e}. 该端口可能被占用，换一个 --port 再试。")
        sys.exit(1)
    s.listen(8)

    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr, args.timeout), daemon=True).start()
    except KeyboardInterrupt:
        log("[SERVER] shutting down")
    finally:
        s.close()

if __name__ == "__main__":
    main()
