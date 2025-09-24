import os
import time
import json
import cv2
import numpy as np
import pyrealsense2 as rs
from xhand_controller import xhand_control

class SyncedReplayer:
    def __init__(self, data_path="recorded_data/motion_and_image_data.json", save_dir="new_recorded_data"):
        self.data_path = data_path
        self.images_dir = os.path.join(os.path.dirname(data_path), "images")
        self._device = xhand_control.XHandControl()
        self._hand_id = 0

        self.save_dir = save_dir
        self.new_images_dir = os.path.join(save_dir, "images")
        os.makedirs(self.new_images_dir, exist_ok=True)
        self.new_data = []

        self.load_data()
        self.open_device()
        self.get_hand_id()

    def load_data(self):
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Data file not found: {self.data_path}")
        with open(self.data_path, "r") as f:
            self.records = json.load(f)
        print(f"Loaded {len(self.records)} frames.")

    def open_device(self):
        device_identifier = {"protocol": "EtherCAT"}
        ether_cat = self._device.enumerate_devices("EtherCAT")
        if ether_cat is None or not ether_cat:
            raise RuntimeError("No EtherCAT device found.")
        rsp = self._device.open_ethercat(ether_cat[0])
        if rsp.error_code != 0:
            raise RuntimeError("Failed to open EtherCAT device.")
        print("EtherCAT device opened.")

    def get_hand_id(self):
        hand_ids = self._device.list_hands_id()
        if not hand_ids:
            raise RuntimeError("No hand ID found.")
        self._hand_id = hand_ids[0]
        print(f"Using hand ID: {self._hand_id}")

    def replay(self, speed_scale=1.0):
        if not self.records:
            print("No records to replay.")
            return

        print("Starting replay... Press 'q' to exit.")

        start_time = self.records[0]["timestamp"]
        for i, frame in enumerate(self.records):
            current_time = frame["timestamp"]

            # ------------------ 控制灵巧手 ------------------
            hand_command = xhand_control.HandCommand_t()
            for finger_info in frame["xhand_data"]:
                fid = finger_info["id"]
                hand_command.finger_command[fid].id = fid
                hand_command.finger_command[fid].kp = 100
                hand_command.finger_command[fid].ki = 0
                hand_command.finger_command[fid].kd = 0
                hand_command.finger_command[fid].position = finger_info["position"]
                hand_command.finger_command[fid].tor_max = 300
                hand_command.finger_command[fid].mode = 3  # 位置模式
            self._device.send_command(self._hand_id, hand_command)

            # ------------------ 显示RGB图像 ------------------
            img_path = os.path.join(self.images_dir, frame["image_filename"])
            if os.path.exists(img_path):
                img = cv2.imread(img_path)
                if img is not None:
                    cv2.imshow('Replay RGB', img)
            else:
                print(f"Image not found: {img_path}")

            # ------------------ 控制时间同步 ------------------
            if i < len(self.records) - 1:
                next_time = self.records[i+1]["timestamp"]
                wait_time = (next_time - current_time) / speed_scale
                wait_time = max(0, wait_time)
                if cv2.waitKey(int(wait_time * 1000)) & 0xFF == ord('q'):
                    break
        cv2.destroyAllWindows()
        print("Replay finished.")

if __name__ == "__main__":
    replayer = SyncedReplayer(
        data_path="recorded_data_uphand/motion_and_image_data.json"
    )
    replayer.replay(speed_scale=1.0)  # 1.0表示原速，0.5表示慢放，2.0表示加速
