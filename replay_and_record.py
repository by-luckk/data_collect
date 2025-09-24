import os
import time
import json
import cv2
import numpy as np
# import pyrealsense2 as rs
import sys
# sys.path.append("/home/slam/Desktop/tactile/xhand_control_python_v1.2.10_20241130_release/xhand_control_python/xhand_control_sdk_py")   # 导入上级目录的模块
from xhand_controller import xhand_control


img_interval = 0.10

class ReplayAndCapture:
    """
    在回放旧动作的同时，再次采集 RealSense RGB 与执行中的手指状态
    """
    def __init__(self,
                 src_json="recorded_data/motion_and_image_data.json",
                 dst_dir="replay_capture",          # 新数据保存目录
                 speed_scale=1.0,                   # 回放倍率
                 kp_rigid=300):                     # 更刚性的 kp
        # ---------- 路径准备 ----------
        self.src_json = src_json
        self.src_img_dir = os.path.join(os.path.dirname(src_json), "images")
        self.dst_dir = dst_dir
        self.dst_img_dir = os.path.join(dst_dir, "images_replay")
        os.makedirs(self.dst_img_dir, exist_ok=True)

        # ---------- 加载旧数据 ----------
        with open(self.src_json, "r") as f:
            self.records = json.load(f)
        print(f"[INFO] Loaded {len(self.records)} frames from {self.src_json}")

        # ---------- 初始化灵巧手 ----------
        self.dev = xhand_control.XHandControl()
        ether_ports = self.dev.enumerate_devices("EtherCAT")
        if not ether_ports:
            raise RuntimeError("No EtherCAT device found")
        if self.dev.open_ethercat(ether_ports[0]).error_code != 0:
            raise RuntimeError("Open EtherCAT failed")
        self.hand_id = self.dev.list_hands_id()[0]
        print(f"[INFO] Hand ID = {self.hand_id}")

        self.kp_rigid = kp_rigid          # 重放时的 kp
        self.speed_scale = speed_scale

        # ---------- 初始化 RealSense ----------
        # self.pipeline = rs.pipeline()
        # cfg = rs.config()
        # cfg.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        # self.pipeline.start(cfg)

        # ---------- 新数据缓存 ----------
        self.new_records = []

    # ===== 主流程 =====
    def run(self):
        print("[INFO] Start replay & recapture ...  (q 退出)")
        last_img_time = time.time()
        for i, frame in enumerate(self.records):
            t_now = time.time()                     # 用当前机器时间做新时间戳

            # ---------------- 控制灵巧手 ----------------
            cmd = xhand_control.HandCommand_t()
            for f in frame["xhand_data"]:
                fid = f["id"]
                c = cmd.finger_command[fid]
                c.id = fid
                c.kp = self.kp_rigid
                c.ki = 0
                c.kd = 1
                c.position = f["position"]
                c.tor_max = 300
                c.mode = 3            # 位置模式
            self.dev.send_command(self.hand_id, cmd)

            # ---------------- 拍摄 RealSense -------------
            # frames = self.pipeline.wait_for_frames()
            # color = frames.get_color_frame()
            # if not color:
            #     print("[WARN] No color frame, skip")
            #     continue
            # img = np.asanyarray(color.get_data())

            # if time.time() - last_img_time >= img_interval:
            #     last_img_time = time.time()
            #     img_name = f"{last_img_time:.6f}.png"
            #     cv2.imwrite(os.path.join(self.dst_img_dir, img_name), img)
            #     img_filename_for_json = img_name
            # else:
            #     img_filename_for_json = None


            # 显示
            # cv2.imshow("Replay RGB Live", img)
            # ---------------- 读取当前手状态 -------------
            err, state = self.dev.read_state(self.hand_id, False)
            if err.error_code != 0:
                print("[WARN] read_state error, code=", err.error_code)
                continue
            cur_state = [
                {"id": s.id,
                 "position": s.position,
                 "torque": s.torque}
                for s in state.finger_state
            ]

            pressure_data = []
            for sensor_idx, sensor in enumerate(state.sensor_data):
                pressure_data.append(
                    {
                        "sensor_id": sensor_idx,
                        "calc_pressure": [
                            sensor.calc_force.fx,
                            sensor.calc_force.fy,
                            sensor.calc_force.fz,
                        ],
                        "raw_pressure": [
                            [f.fx, f.fy, f.fz] for f in sensor.raw_force
                        ]
                    }
                )


            # ---------------- 保存一帧 -------------------
            self.new_records.append({
                "timestamp": t_now,
                "xhand_data": cur_state,
                # "image_filename": img_filename_for_json,
                "pressure_data": pressure_data
            })

            # ----------- 计算下一帧等待时间 --------------
            if i < len(self.records) - 1:
                dt = (self.records[i + 1]["timestamp"] -
                      self.records[i]["timestamp"]) / self.speed_scale
                dt = max(0, dt)
            else:
                dt = 0

            time.sleep(dt)
            # 处理键盘事件 & 等待
            # if cv2.waitKey(int(dt * 1000)) & 0xFF == ord('q'):
            #     print("[INFO] Manual quit")
            #     break

        # ========== 善后 ==========
        # self.pipeline.stop()
        cv2.destroyAllWindows()
        out_json = os.path.join(self.dst_dir, "motion_and_image_data_replay.json")
        with open(out_json, "w") as f:
            json.dump(self.new_records, f, indent=4)
        print(f"[INFO] New data saved to {out_json}")
        print("[INFO] Replay & capture finished.")


if __name__ == "__main__":
    player = ReplayAndCapture(
        src_json="press_cube/motion_and_image_data.json",
        dst_dir="press_cube/slide2",
        speed_scale=1.0,   # 1.0 原速；0.5 慢放；2.0 快放
        kp_rigid=100       # 手指刚性
    )
    player.run()
