import os
import time
import json
from xhand_controller import xhand_control

class XHandRecorder:
    def __init__(self, save_path="xhand_motion_record.json", interval=0.05):
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
        self._save_path = save_path
        self._interval = interval  # 采样间隔 (秒)

        # 初始化通信协议
        device_identifier = {"protocol": "EtherCAT"}  # 你也可以换成 RS485
        self.open_device(device_identifier)
        self.get_hand_id()

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

    def record_motion(self, record_time=10):
        """
        record_time: 录制的总时长 (秒)
        """
        print(f"Start recording motion for {record_time} seconds...")
        all_records = []
        start_time = time.time()

        while time.time() - start_time < record_time:
            error_struct, state = self._device.read_state(self._hand_id, False)
            if error_struct.error_code != 0:
                print(f"Read state error: {self.parse_error_code(error_struct)}")
                time.sleep(self._interval)
                continue

            # 保存一帧的数据
            frame_data = {
                "timestamp": time.time(),
                "finger_commands": []
            }

            for finger_state in state.finger_state:
                finger_info = {
                    "id": finger_state.id,
                    "position": finger_state.position,
                    "torque": finger_state.torque
                }
                frame_data["finger_commands"].append(finger_info)

            all_records.append(frame_data)
            print(f"Recorded frame at {frame_data['timestamp']}")
            time.sleep(self._interval)

        # 保存到文件
        with open(self._save_path, "w") as f:
            json.dump(all_records, f, indent=4)

        print(f"Motion recording finished. Data saved to {self._save_path}")

    def parse_error_code(self, error_struct):
        """辅助函数，解析错误信息"""
        return f"Error code: {error_struct.error_code}"

    def close(self):
        # self._device.close()
        print("Device closed.")

if __name__ == "__main__":
    recorder = XHandRecorder(
        save_path="recorded_data/xhand_motion_record.json",  # 保存文件名
        interval=0.05                          # 每隔50ms记录一次 (约20Hz)
    )

    try:
        # 录制10秒钟，可以根据需要修改
        recorder.record_motion(record_time=1)
    finally:
        recorder.close()
