import os
import time
import json
import cv2
import numpy as np
from xhand_controller import xhand_control
from utils import create_pressure_visualization

def press_enter_for_next_step():
    """等待用户按回车键进入下一步"""
    while True:
        user_input = input("按回车进入下一步：")
        if user_input == "":
            break
        else:
            print(f"You entered: {user_input}")

class XHandRecorder:
    def __init__(self, save_dir="recorded_xhand_data", interval=1/60, enable_visualization=True):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        self.data = []  # 保存所有xhand记录
        self.interval = interval
        self.enable_visualization = enable_visualization

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
        
        # 初始化可视化窗口
        if self.enable_visualization:
            cv2.namedWindow('XHand Pressure Visualization', cv2.WINDOW_AUTOSIZE)
            print("[INFO] Pressure visualization window initialized. Press 'q' to quit.")

    def open_device(self, device_identifier):
        """打开xhand设备"""
        if device_identifier["protocol"] == "EtherCAT":
            ether_cat = self._device.enumerate_devices("EtherCAT")
            rsp = self._device.open_ethercat(ether_cat[0])
        else:
            raise ValueError("Only EtherCAT supported.")

    def get_hand_id(self):
        """获取灵巧手ID"""
        hand_ids = self._device.list_hands_id()
        self._hand_id = hand_ids[0]

    def record(self, record_time=10, warmup_frames=15):
        """记录xhand数据"""
        self._clear_previous_record()
        print(f"[INFO] Cleared previous data, start warm-up …")
        print(f"Skip first {warmup_frames} frames for warm-up …")
        
        # ① --- 丢弃手部前warmup_frames帧 ---------------------------------
        for _ in range(warmup_frames):
            _, state = self._device.read_state(self._hand_id, False)
            time.sleep(self.interval)                # 维持节拍
        
        # ② --- 真正开始计时录制 -----------------------------------
        press_enter_for_next_step()
        print(f"Start xhand recording for {record_time} seconds...")
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

                # 提取手指数据
                xhand_frame = [
                    {
                        "id": finger.id,
                        "position": finger.position,
                        "torque": finger.torque
                    }
                    for finger in state.finger_state
                ]

                # 提取压力传感器数据
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

                # 记录一条数据
                record = {
                    "timestamp": timestamp,
                    "xhand_data": xhand_frame,
                    "pressure_data": pressure_data
                }
                self.data.append(record)

                # 实时可视化压力数据
                if self.enable_visualization and len(pressure_data) >= 5:
                    try:
                        vis_image = create_pressure_visualization(pressure_data)
                        if vis_image is not None:
                            cv2.imshow('XHand Pressure Visualization', vis_image)
                            
                            # 检查是否按下'q'键退出
                            if cv2.waitKey(1) & 0xFF == ord('q'):
                                print("Manual stop detected (pressed 'q').")
                                break
                    except Exception as e:
                        print(f"Visualization error: {e}")

                print(f"Recorded xhand frame at {timestamp:.6f}")
                time.sleep(self.interval)
                
        finally:
            # 关闭可视化窗口
            if self.enable_visualization:
                cv2.destroyAllWindows()
            
            # 保存整体数据
            with open(os.path.join(self.save_dir, "xhand_data.json"), "w") as f:
                json.dump(self.data, f, indent=4)
            print(f"XHand data saved to {self.save_dir}")
            print(f"Total recorded frames: {len(self.data)}")

    def _clear_previous_record(self):
        """删除旧数据，清空内存中的列表"""
        # 删除旧json文件
        json_path = os.path.join(self.save_dir, "xhand_data.json")
        if os.path.exists(json_path):
            os.remove(json_path)

        # 清空内存中的列表
        self.data = []

    def close(self):
        """关闭设备连接"""
        if self.enable_visualization:
            cv2.destroyAllWindows()
        if hasattr(self, '_device'):
            self._device.close()

if __name__ == "__main__":
    recorder = XHandRecorder(
        save_dir="data/xhand_only_0924",
        interval=0.20,  # 20Hz
        enable_visualization=True  # 启用实时可视化
    )
    
    try:
        recorder.record(record_time=30)
    finally:
        recorder.close()
