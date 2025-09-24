import os
import time
import json
import cv2
import numpy as np
import math
import platform
from xhand_controller import xhand_control
from utils import create_pressure_visualization

# 根据操作系统导入相应的模块
if platform.system() == 'Windows':
    from Release.windows import xCoreSDK_python
elif platform.system() == 'Linux':
    from Release.linux import xCoreSDK_python
else:
    raise ImportError("Unsupported operating system")

def press_enter_for_next_step():
    """等待用户按回车键进入下一步"""
    while True:
        user_input = input("按回车进入下一步：")
        if user_input == "":
            break
        else:
            print(f"You entered: {user_input}")

def is_ok(ec):
    """检查错误码是否表示成功"""
    # 空、None 都视为成功
    if ec is None or ec == {} or ec == []:
        return True

    # 数字：0 成功
    if isinstance(ec, (int, float)):
        return int(ec) == 0

    # 字符串：匹配常见"成功"文案
    if isinstance(ec, str):
        return ec.strip() in ("操作成功完成", "成功", "OK", "Ok", "ok", "Success", "success", "Succeeded")

    # 字典：看常见字段
    if isinstance(ec, dict):
        for k in ("code", "errCode", "error_code"):
            if k in ec:
                try:
                    return int(ec[k]) == 0
                except Exception:
                    pass
        msg = str(ec.get("msg", "")).strip()
        if msg:
            return msg in ("操作成功完成", "成功", "OK", "Ok", "ok", "Success", "success", "Succeeded")
        # 如果有 error/enum
        if "error" in ec and hasattr(xCoreSDK_python, "ErrorCode") and hasattr(xCoreSDK_python.ErrorCode, "success"):
            return ec["error"] == xCoreSDK_python.ErrorCode.success
        # 未识别则保守当失败
        return False

    # 具有属性的错误对象
    for attr in ("code", "errCode", "error_code"):
        if hasattr(ec, attr):
            try:
                return int(getattr(ec, attr)) == 0
            except Exception:
                pass
    if hasattr(ec, "msg"):
        if str(getattr(ec, "msg")).strip() in ("操作成功完成", "成功", "OK", "Ok", "ok", "Success", "success", "Succeeded"):
            return True

    # 兜底：未知类型 -> 失败
    return False

class XHandPostureRecorder:
    def __init__(self, save_dir="recorded_xhand_posture_data", interval=1/60, enable_visualization=True, robot_ip="192.168.2.160"):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        self.data = []  # 保存所有xhand和posture记录
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
        
        # 初始化机械臂
        self.robot_ip = robot_ip
        self.robot = None
        self.robot_ec = {}
        self.init_robot()
        
        # 初始化可视化窗口
        if self.enable_visualization:
            cv2.namedWindow('XHand Pressure Visualization', cv2.WINDOW_AUTOSIZE)
            print("[INFO] Pressure visualization window initialized. Press 'q' to quit.")

    def init_robot(self):
        """初始化机械臂连接"""
        try:
            self.robot = xCoreSDK_python.xMateRobot(self.robot_ip)
            self.robot_ec = {}
            print(f"[INFO] Robot connected to {self.robot_ip}")
        except Exception as e:
            print(f"[ERROR] Failed to connect to robot: {e}")
            self.robot = None

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

    def get_robot_posture(self):
        """获取机械臂当前位姿"""
        if self.robot is None:
            return None
        
        try:
            pos = self.robot.posture(xCoreSDK_python.CoordinateType.flangeInBase, self.robot_ec)
            
            if not is_ok(self.robot_ec):
                print(f"[WARNING] Failed to get robot posture: {self.robot_ec}")
                return None
            
            # 解析数据
            x, y, z = pos[:3]  # 平移量 (单位：米)
            a, b, c = pos[3:]  # 旋转量 (单位：弧度)
            
            # 转换为度
            a_deg = a * 180 / math.pi
            b_deg = b * 180 / math.pi
            c_deg = c * 180 / math.pi
            
            # 转换为毫米
            x_mm = x * 1000
            y_mm = y * 1000
            z_mm = z * 1000
            
            return {
                "position_mm": [x_mm, y_mm, z_mm],
                "position_m": [x, y, z],
                "orientation_rad": [a, b, c],
                "orientation_deg": [a_deg, b_deg, c_deg]
            }
        except Exception as e:
            print(f"[ERROR] Error getting robot posture: {e}")
            return None

    def record(self, record_time=10, warmup_frames=15):
        """记录xhand和机械臂数据"""
        self._clear_previous_record()
        print(f"[INFO] Cleared previous data, start warm-up …")
        print(f"Skip first {warmup_frames} frames for warm-up …")
        
        # ① --- 丢弃手部前warmup_frames帧 ---------------------------------
        for _ in range(warmup_frames):
            _, state = self._device.read_state(self._hand_id, False)
            if self.robot is not None:
                self.get_robot_posture()  # 预热机械臂读取
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

                # 获取机械臂位姿
                robot_posture = self.get_robot_posture()

                # 记录一条数据
                record = {
                    "timestamp": timestamp,
                    "xhand_data": xhand_frame,
                    "pressure_data": pressure_data,
                    "robot_posture": robot_posture
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

                print(f"Recorded frame at {timestamp:.6f} - Robot: {'OK' if robot_posture else 'Failed'}")
                time.sleep(self.interval)
                
        finally:
            # 关闭可视化窗口
            if self.enable_visualization:
                cv2.destroyAllWindows()
            
            # 保存整体数据
            with open(os.path.join(self.save_dir, "xhand_posture_data.json"), "w") as f:
                json.dump(self.data, f, indent=4)
            print(f"XHand and posture data saved to {self.save_dir}")
            print(f"Total recorded frames: {len(self.data)}")

    def _clear_previous_record(self):
        """删除旧数据，清空内存中的列表"""
        # 删除旧json文件
        json_path = os.path.join(self.save_dir, "xhand_posture_data.json")
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
    recorder = XHandPostureRecorder(
        save_dir="data/xhand_posture_0924",
        interval=0.20,  # 20Hz
        enable_visualization=True,  # 启用实时可视化
        robot_ip="192.168.2.160"  # 机械臂IP地址
    )
    
    try:
        recorder.record(record_time=30)
    finally:
        recorder.close()
