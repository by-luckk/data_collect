import os
import time
import json
import cv2
import numpy as np
import pyrealsense2 as rs
from xhand_controller import xhand_control
import shutil
def press_enter_for_next_step():

    while True:
        user_input = input("按回车进入下一步：")
        if user_input == "":
            break
        else:
            print(f"You entered: {user_input}")

class SynchronizedRecorder:
    def __init__(self, save_dir="recorded_data", interval=1/60):
        self.save_dir = save_dir
        self.images_dir = os.path.join(save_dir, "images")
        os.makedirs(self.images_dir, exist_ok=True)
        self.data = []  # 保存所有同步记录
        self.interval = interval

        # 初始化灵巧手
        self._device = xhand_control.XHandControl()
        self._hand_command = xhand_control.HandCommand_t()
        for i in range(12):
            self._hand_command.finger_command[i].id = i
            self._hand_command.finger_command[i].kp = 300
            self._hand_command.finger_command[i].ki = 0
            self._hand_command.finger_command[i].kd = 0
            self._hand_command.finger_command[i].position = 0
            self._hand_command.finger_command[i].tor_max = 300
            self._hand_command.finger_command[i].mode = 3
        device_identifier = {"protocol": "EtherCAT"}
        self.open_device(device_identifier)
        self.get_hand_id()

        # 初始化RealSense
        self.pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        self.pipeline.start(config)

    def open_device(self, device_identifier):
        if device_identifier["protocol"] == "EtherCAT":
            ether_cat = self._device.enumerate_devices("EtherCAT")
            rsp = self._device.open_ethercat(ether_cat[0])
        else:
            raise ValueError("Only EtherCAT supported.")

    def get_hand_id(self):
        hand_ids = self._device.list_hands_id()
        self._hand_id = hand_ids[0]

    def record(self, record_time=10, warmup_frames=15):
        self._clear_previous_record()
        print(f"[INFO] Cleared previous data, start warm-up …")
        print(f"Skip first {warmup_frames} frames for warm-up …")
        # ① --- 丢弃相机&手部前30帧 ---------------------------------
        for _ in range(warmup_frames):
            self.pipeline.wait_for_frames()          # 取帧但不处理
            _, state = self._device.read_state(self._hand_id, False)
            time.sleep(self.interval)                # 维持节拍
        # ② --- 真正开始计时录制 -----------------------------------
        press_enter_for_next_step()
        print(f"Start synchronized recording for {record_time} seconds...")
        start_time = time.time()

        try:
            while time.time() - start_time < record_time:
                # 统一采样时间
                timestamp = time.time()

                # 读取灵巧手状态
                error_struct, state = self._device.read_state(self._hand_id, False)
                if error_struct.error_code != 0:
                    print(f"Read xhand error, skip one frame.")
                    continue

                xhand_frame = [
                    {
                        "id": finger.id,
                        "position": finger.position,
                        "torque": finger.torque
                    }
                    for finger in state.finger_state
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
                print(pressure_data)

                # 捕获一张RGB图
                frames = self.pipeline.wait_for_frames()
                color_frame = frames.get_color_frame()
                if color_frame is None:
                    print("No color frame captured, skip one frame.")
                    continue
                img = np.asanyarray(color_frame.get_data())

                # 保存图像
                img_filename = f"{timestamp:.6f}.png"
                img_path = os.path.join(self.images_dir, img_filename)
                cv2.imwrite(img_path, img)

                # ------- 🔥新增：实时显示图像 --------
                cv2.imshow('RealSense RGB Live', img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("Manual stop detected.")
                    break
                # -------------------------------------

                # 记录一条数据
                record = {
                    "timestamp": timestamp,
                    "xhand_data": xhand_frame,
                    "pressure_data": pressure_data,
                    "image_filename": img_filename
                }
                self.data.append(record)

                print(f"Recorded frame at {timestamp:.6f}")
                time.sleep(self.interval)
        finally:
            # self._device.close()
            self.pipeline.stop()

            # 保存整体数据
            with open(os.path.join(self.save_dir, "motion_and_image_data.json"), "w") as f:
                json.dump(self.data, f, indent=4)
            print(f"Data saved to {self.save_dir}")
    def _clear_previous_record(self):
        """删除旧图片、旧 json，并把 self.data 置空。"""
        # 1) 删除 images 目录整个文件夹，然后重新创建
        if os.path.exists(self.images_dir):
            shutil.rmtree(self.images_dir)
        os.makedirs(self.images_dir, exist_ok=True)
        
        # 2) 删除旧 json
        json_path = os.path.join(self.save_dir, "motion_and_image_data.json")
        if os.path.exists(json_path):
            os.remove(json_path)

        # 3) 清空内存中的列表
        self.data = []


if __name__ == "__main__":
    recorder = SynchronizedRecorder(
        save_dir="recorded_pressure_rgb",
        interval=0.20  # 20Hz
    )
    # recorder.record(record_time=30)
    recorder.record(record_time=30)

