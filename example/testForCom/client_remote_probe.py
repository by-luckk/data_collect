#!/usr/bin/env python3
import socket, struct, json, argparse, time
from typing import Tuple

FX, FY = 607.378, 607.371
CX, CY = 309.53, 248.267
WIDTH, HEIGHT = 640, 480

def classify(exc: Exception) -> str:
    import errno, socket as sk
    if isinstance(exc, TimeoutError) or isinstance(exc, sk.timeout):
        return "TIMEOUT(像是被防火墙/安全组丢弃)"
    if isinstance(exc, ConnectionRefusedError):
        return "REFUSED(主机可达但该端口无服务或被RST拒绝)"
    if isinstance(exc, OSError) and getattr(exc, "errno", None) == errno.EHOSTUNREACH:
        return "HOST_UNREACHABLE(主机不可达/路由问题)"
    return f"ERROR({exc.__class__.__name__})"

def try_one(server: str, port: int, timeout: float) -> Tuple[str, dict]:
    header = {
        "width": HEIGHT and WIDTH,  # 仅占位
        "height": HEIGHT,
        "fx": FX, "fy": FY, "cx": CX, "cy": CY,
        "rgb_format": "none", "depth_format": "none",
        "rgb_size": 0, "depth_size": 0
    }
    hbytes = json.dumps(header).encode("utf-8")
    t0 = time.time()
    with socket.create_connection((server, port), timeout=timeout) as s:
        s.settimeout(timeout)
        # 发送头（零负载）
        s.sendall(struct.pack(">I", len(hbytes))); s.sendall(hbytes)
        # 读 4 字节长度
        def recvn(n):
            b = bytearray()
            while len(b) < n:
                chunk = s.recv(n - len(b))
                if not chunk:
                    raise ConnectionError("对端关闭了连接")
                b.extend(chunk)
            return bytes(b)
        raw_len = recvn(4)
        resp_len = struct.unpack(">I", raw_len)[0]
        if resp_len <= 0 or resp_len > 5_000_000:
            raise ValueError(f"响应长度异常={resp_len}，可能是非本协议服务")
        resp = json.loads(recvn(resp_len).decode("utf-8"))
        dt = time.time() - t0
        return (f"OK({dt:.3f}s)", resp)

def probe(server: str, ports, timeout: float):
    print(f"[PROBE] target={server}, timeout={timeout}s, ports={ports}")
    for p in ports:
        print(f"\n[PROBE] === PORT {p} ===")
        try:
            status, resp = try_one(server, p, timeout)
            print(f"[RESULT] {p}: {status}")
            print(f"[JSON]   {json.dumps(resp)[:300]}{'...' if len(json.dumps(resp))>300 else ''}")
            if resp.get("status") != "ok":
                print("[WARN]   对端返回非 ok，可能不是我们的测试服务。")
        except Exception as e:
            print(f"[RESULT] {p}: {classify(e)}")
            if p == 80:
                print("[NOTE]   端口 80 是低位端口，普通用户无法在服务器上开启自定义TCP服务；需要管理员配置反向代理或提权。")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="115.190.27.42")
    ap.add_argument("--ports", default="3030,80")
    ap.add_argument("--timeout", type=float, default=8.0)
    args = ap.parse_args()
    ports = [int(x) for x in args.ports.split(",") if x.strip()]
    probe(args.server, ports, args.timeout)

if __name__ == "__main__":
    main()
