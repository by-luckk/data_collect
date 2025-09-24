import cv2

def send_one_frame(rgb_bgr, depth_z16):
    # 压缩为 PNG：RGB 8UC3，Depth 16UC1
    ok_rgb,  rgb_buf  = cv2.imencode(".png", rgb_bgr)            # BGR 排列没关系，服务端只需要像素对齐
    ok_dep,  dep_buf  = cv2.imencode(".png", depth_z16)          # 必须保持 uint16
    assert ok_rgb and ok_dep, "PNG encode failed"

    header = {
        "width": WIDTH, "height": HEIGHT,
        "fx": FX, "fy": FY, "cx": CX, "cy": CY,
        "rgb_format": "png", "depth_format": "png",
        "rgb_size": int(len(rgb_buf)), "depth_size": int(len(dep_buf))
    }
    header_bytes = json.dumps(header).encode("utf-8")

    with socket.create_connection((SERVER_IP, SERVER_PORT), timeout=5.0) as s:
        # 发送：4字节头长度 + 头 + RGB + DEPTH
        s.sendall(struct.pack(">I", len(header_bytes)))
        s.sendall(header_bytes)
        s.sendall(rgb_buf.tobytes())
        s.sendall(dep_buf.tobytes())

        # 接收：4字节应答长度 + JSON
        resp_len = struct.unpack(">I", recvall(s, 4))[0]
        resp = json.loads(recvall(s, resp_len).decode(
        cfg.enable_stream(rs.stream.depth, WIDTH, HEIGHT, rs.format.z16, FPS)
        cfg.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, FPS)
        profile = pipeline.start(cfg)

    align = rs.align(rs.stream.color)  # 让 depth 对齐到
        while True:
            frames = pipeline.wait_for_frames()
            aligned = align.process(frames)
            depth = aligned.get_depth_frame()
            color = aligned.get_color_frame()
            if not depth or not color:
                continue

            # 转 numpy
            depth_np = np.asanyarray(depth.get_data())          # HxW, uint16（毫米或内部单位由 RealSense 决定）
            color_np = np.asanyarray(color.get_data())          # HxWx3, uint8 BGR

            # 基本一致性检查
            assert depth_np.shape == (HEIGHT, WIDTH) and color_np.shape[:2] == (HEIGHT, WIDTH)

            # 预览
            show = color_np.copy()
            cv2.imshow("RGB (aligned target)", show)
            key = cv2.waitKey(1) & 0xFF

            if key == ord(' '):
                t0 = time.time()
                resp = send_one_frame(color_np, depth_np)
                print("[RESP]", resp)
                if resp.get("status") == "ok":
                    T = np.array(resp["T"], dtype=float)
                    # 这里可以直接把 T 用于后续控制（例如基于 T 计算机器人姿态目标）
                    print("[T]\n", T)
                else:
                    print("[ERROR]", resp)
                print(f"[INFO] round-trip {time.time()-t0:.3f}s")
            elif key == ord('q'):
                break
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
