import os
import time
import json
from xhand_controller import xhand_control

class XHandReplayer:
    def __init__(self, record_path="xhand_motion_record.json", speed_scale=1.0):
        self._hand_id = 0
        self._device = xhand_control.XHandControl()
        self._hand_command = xhand_control.HandCommand_t()
        for i in range(12):
            self._hand_command.finger_command[i].id = i
            self._hand_command.finger_command[i].kp = 100
            self._hand_command.finger_command[i].ki = 0
            self._hand_command.finger_command[i].kd = 0
            self._hand_command.finger_command[i].position = 0
            self._hand_command.finger_command[i].tor_max = 300
            self._hand_command.finger_command[i].mode = 3
        self._record_path = record_path
        self._speed_scale = speed_scale  # 回放的速度倍率，1.0 = 实时速度

        # 初始化通信协议
        device_identifier = {"protocol": "EtherCAT"}  # 你可以换成 RS485
        self.open_device(device_identifier)
        self.get_hand_id()

        # 加载录制的数据
        self.load_motion_data()

    def open_device(self, device_identifier):
        if device_identifier["protocol"] == "RS485":
            device_identifier["baud_rate"] = int(device_identifier["baud_rate"])
            rsp = self._device.open_serial(
                device_identifier["serial_port"],
                device_identifier["baud_rate"],
            )
            print(f"open RS485 result: {rsp.error_code == 0}\n")
        elif device_identifier["protocol"] == "EtherCAT":
            ether_cat = self._device.enumerate_devices("EtherCAT")
            if ether_cat is None or not ether_cat:
                raise RuntimeError("No EtherCAT device found.")
            rsp = self._device.open_ethercat(ether_cat[0])
            print(f"open EtherCAT result: {rsp.error_code == 0}\n")
        else:
            raise ValueError("Unsupported protocol.")

    def get_hand_id(self):
        hand_ids = self._device.list_hands_id()
        if not hand_ids:
            raise RuntimeError("No hand ID found.")
        self._hand_id = hand_ids[0]
        print(f"Connected to hand ID: {self._hand_id}")

    def load_motion_data(self):
        if not os.path.exists(self._record_path):
            raise FileNotFoundError(f"Motion record file not found: {self._record_path}")

        with open(self._record_path, "r") as f:
            self.motion_data = json.load(f)
        
        print(f"Loaded {len(self.motion_data)} frames from {self._record_path}")

    def replay_motion(self):
        if not self.motion_data:
            print("No motion data to replay.")
            return

        print("Starting motion replay...")

        start_time = self.motion_data[0]["timestamp"]
        for i, frame in enumerate(self.motion_data):
            # 生成目标手指动作
            hand_command = xhand_control.HandCommand_t()
            for finger_info in frame["finger_commands"]:
                fid = finger_info["id"]
                hand_command.finger_command[fid].id = fid
                hand_command.finger_command[fid].kp = 100
                hand_command.finger_command[fid].ki = 0
                hand_command.finger_command[fid].kd = 0
                hand_command.finger_command[fid].position = finger_info["position"]
                hand_command.finger_command[fid].tor_max = 300
                hand_command.finger_command[fid].mode = 3  # 位置模式

            # 发送指令
            self._device.send_command(self._hand_id, hand_command)

            # 控制时间间隔，使回放速度一致
            if i < len(self.motion_data) - 1:
                time_diff = self.motion_data[i+1]["timestamp"] - frame["timestamp"]
                time.sleep(time_diff / self._speed_scale)

        print("Motion replay finished.")

    def close(self):
        # self._device.close()
        print("Device closed.")

if __name__ == "__main__":
    replayer = XHandReplayer(
        record_path="recorded_data/xhand_motion_record.json",  # 之前录制的数据
        speed_scale=1.0                           # 1.0是实时回放, >1是加速, <1是慢放
    )

    try:
        replayer.replay_motion()
    finally:
        replayer.close()
