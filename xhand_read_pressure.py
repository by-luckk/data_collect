import os
import time
import json
from xhand_controller import xhand_control

# 设置 LD_LIBRARY_PATH 环境变量
script_dir = os.path.dirname(os.path.realpath(__file__))
xhandcontrol_library_dir = os.path.join(script_dir, "lib")
os.environ["LD_LIBRARY_PATH"] = (
    xhandcontrol_library_dir + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
)
print(f"LD_LIBRARY_PATH: {os.environ['LD_LIBRARY_PATH']}\n")

class XHandControlExample:
    def __init__(self):
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

    def exam_enumerate_devices(self, protocol: str):
        serial_port = self._device.enumerate_devices(protocol)
        print(f"xhand devices port: {serial_port}\n")
        return serial_port

    def exam_open_device(self, device_identifier: dict):
        # RS485
        if device_identifier["protocol"] == "RS485":
            device_identifier["baud_rate"] = int(device_identifier["baud_rate"])
            rsp = self._device.open_serial(
                device_identifier["serial_port"],
                device_identifier["baud_rate"],
            )
            print(f"open RS485 result: {rsp.error_code == 0}\n")
        # EtherCAT
        elif device_identifier["protocol"] == "EtherCAT":
            ether_cat = self.exam_enumerate_devices("EtherCAT")
            print(f"enumerate_devices_ethercat ether_cat= {ether_cat}\n")
            if ether_cat is None or not ether_cat:
                print("enumerate_devices_ethercat get empty \n")
            rsp = self._device.open_ethercat(ether_cat[0])
            print(f"open EtherCAT result: {rsp.error_code == 0}\n")

    def exam_list_hands_id(self):
        self._hand_id = self._device.list_hands_id()[0]
        print(f"hand_id: {self._hand_id}\n")

    def exam_set_hand_id(self, new_id):
        hands_id = self._device.list_hands_id()
        print(f"set hand_id before:{hands_id[0]}\n")
        old_id = hands_id[0]
        err_struct = self._device.set_hand_id(old_id, new_id)
        if err_struct.error_code == 0:
            self._hand_id = new_id
        hands_id = self._device.list_hands_id()
        print(f"set hand_id after:{hands_id[0]}\n")
        print(f"xhand set_hand_id result: {err_struct.error_code == 0}\n")

    def exam_read_device_info(self):
        error_struct, info = self._device.read_device_info(self._hand_id)
        print(f"xhand serial_number:{info.serial_number[0:16]}") # sn is 16 bytes
        print(f"xhand hand_id:{info.hand_id}")
        print(f"xhand hand_id:{info.ev_hand}\n")

    def exam_serial_number(self):
        error_struct, serial_number = self._device.get_serial_number(self._hand_id)
        print(f"xhand serial_number: {serial_number}\n")

    def exam_get_hand_type(self):
        error_struct, hand_type = self._device.get_hand_type(self._hand_id)
        print(f"xhand hand_type: {hand_type}\n")

    def exam_read_version(self):
        joint_id = 0
        error_struct, version = self._device.read_version(self._hand_id, joint_id)
        print(f"xhand hardware SDK version: {version}\n")
            
    def exam_send_command(self):
        print(f"xhand send_command result: { self._device.send_command(self._hand_id, self._hand_command).error_code == 0}\n")

    def exam_read_state(self):
        error_struct, state = self._device.read_state(self._hand_id, False)
        if error_struct.error_code != 0:
            print(f"xhand read_state error:{self.parse_error_code(error_struct)}\n")
            return
        
        finger_1 = state.finger_state[2]
        print(f"|+| finger.id = {finger_1.id}, finger.temperature = {finger_1.temperature} ")
        print(f"|+| finger.id = {finger_1.id}, finger.temperature & 0xFF = {finger_1.temperature & 0xFF} ")
        print(f"|+| finger.id = {finger_1.id}, finger.commboard_err = {finger_1.commboard_err} ")
        print(f"|+| finger.id = {finger_1.id}, finger.jonitboard_err = {finger_1.jonitboard_err} ")
        print(f"|+| finger.id = {finger_1.id}, finger.tipboard_err = {finger_1.tipboard_err} ")

        # Fingertip sensor state
        fingertip_state = {}
        if finger_1.id == 2:
            sensor_data = state.sensor_data[0]
            fingertip_state["calc_pressure"] = [
                sensor_data.calc_force.fx,
                sensor_data.calc_force.fy,
                sensor_data.calc_force.fz,
            ]
            fingertip_state["raw_pressure"] = [
                [force.fx, force.fy, force.fz]
                for force in state.sensor_data[0].raw_force
            ]
            fingertip_state["sensor_temperature"] = sensor_data.calc_temperature

        print(f"|+| finger.id = {finger_1.id}, fingertip calc_pressure = {fingertip_state['calc_pressure']}")
        print(f"|+| finger.id = {finger_1.id}, fingertip raw_pressure = {fingertip_state['raw_pressure']}")
        print(f"|+| finger.id = {finger_1.id}, fingertip sensor_temperature = {fingertip_state['sensor_temperature']}\n")

    def exam_read_pressure(self, json_path="xhand_pressure_data.json", interval=0.1):
        """
        持续读取压力数据并保存到JSON文件中，每次追加一组新的数据。
        
        参数：
        - json_path：str，保存路径
        - interval：float，每次采样之间的间隔时间（秒）
        """
        print("Starting continuous pressure data collection...")
            # 如果文件不存在，先初始化为空列表
        if not os.path.exists(json_path):
            with open(json_path, "w") as f:
                json.dump([], f)
        
        try:
            while True:
                error_struct, state = self._device.read_state(self._hand_id, False)
                if error_struct.error_code != 0:
                    print(f"xhand read_state error:{self.parse_error_code(error_struct)}\n")
                    time.sleep(interval)
                    continue

                print("state len", len(state.finger_state), len(state.sensor_data))

                # 组织本次采样数据
                sample_data = {
                    "timestamp": time.time(),  # 增加采样时间戳
                    "finger_positions": [],
                    "finger_data": []
                }

                for finger_state in state.finger_state:
                    print(finger_state.position)
                    sample_data["finger_positions"].append(finger_state.position)

                for sensor_id in range(len(state.sensor_data)):
                    fingertip_state = {}
                    sensor_data = state.sensor_data[sensor_id]
                    fingertip_state["calc_pressure"] = [
                        sensor_data.calc_force.fx,
                        sensor_data.calc_force.fy,
                        sensor_data.calc_force.fz,
                    ]
                    fingertip_state["raw_pressure"] = [
                        [force.fx, force.fy, force.fz]
                        for force in sensor_data.raw_force
                    ]
                    fingertip_state["sensor_temperature"] = sensor_data.calc_temperature
                    fingertip_state["raw_temperature"] = [
                        temp for temp in sensor_data.temperature
                    ]
                    sample_data["finger_data"].append(fingertip_state)
                
                # 读回已有的数据
                with open(json_path, "r") as f:
                    all_data = json.load(f)

                # 追加当前数据
                all_data.append(sample_data)

                with open(json_path, "w") as f:
                    json.dump(all_data, f, indent=4)
                print(f"Data dumped to {json_path}")
                print(f"Sample collected at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sample_data['timestamp']))}")
                # 等待一段时间再采样
                time.sleep(interval)

        except KeyboardInterrupt:
            print("Data collection stopped by user.")
    def exam_reset_sensor(self):
        sensor_id = 17
        print(f"xhand reset_sensor result: {self._device.reset_sensor(self._hand_id, sensor_id).error_code == 0}\n")

    def exam_close_device(self):
        print(f"xhand device closed\n")
	
    def set_hand_mode(self, mode: int):
        hand_mode = xhand_control.HandCommand_t()
        for i in range(12):
            hand_mode.finger_command[i].id = i
            hand_mode.finger_command[i].kp = 0
            hand_mode.finger_command[i].ki = 0
            hand_mode.finger_command[i].kd = 0
            hand_mode.finger_command[i].position = 0
            hand_mode.finger_command[i].tor_max = 0
            hand_mode.finger_command[i].mode = mode
        self._device.send_command(self._hand_id, hand_mode)
        time.sleep(1)

    def exam_calibrate_joint_by_mold(self):
        hand_id = self._device.list_hands_id()
        tools = "S1"
        step = 1
        calibrated_angles = [10, 60, 30, 0, 10, 10, 10, 10, 10, 10, 10, 10]
        joints_limit_arr = [ 0, 105, -60, 90, -10, 105, -10, 10, 0, 110, 0, 110, 0,  110, 0, 110, 0, 110, 0, 110, 0, 110, 0, 110]
        self.set_hand_mode(mode=0)
        error_struct = self._device.calibrate_joint_by_mold(hand_id[0], tools, step, calibrated_angles, joints_limit_arr)
        print(f"xhand calibrate_joint_by_mold result: {error_struct.error_code == 0}") 

    def exam_get_sdk_version(self):
        print(f"xhand software SDK version: {self._device.get_sdk_version()}\n")

if __name__ == "__main__":
    xhand_exam = XHandControlExample()

    # 通讯方式二选一，当前支持 EtherCAT 和 RS485
    # First of all, open device 
    device_identifier = {}
    # EtherCAT
    device_identifier['protocol'] = 'EtherCAT'
    xhand_exam.exam_open_device(device_identifier)

    # RS485
    # device_identifier['protocol'] = 'RS485'
    # # 可以使用 exam_enumerate_devices('RS485) 读取串口列表信息，选择 ttyUSB 前缀的串口
    # # Get serial port list, choose ttyUSB*
    # xhand_exam.exam_enumerate_devices('RS485')
    # device_identifier["serial_port"] = '/dev/ttyUSB0'
    # device_identifier['baud_rate'] = 3000000
    # xhand_exam.exam_open_device(device_identifier)

    # Then, get hands id
    xhand_exam.exam_list_hands_id()

    xhand_exam.exam_get_sdk_version()
    xhand_exam.exam_read_version()
    xhand_exam.exam_get_hand_type()
    xhand_exam.exam_serial_number()

    xhand_exam.exam_read_state()
    xhand_exam.exam_read_device_info()

    # xhand_exam.exam_reset_sensor()
    # xhand_exam.exam_set_hand_id(new_id=1)
    print("wait!")
    time.sleep(1)
    xhand_exam.exam_read_pressure()

    # 当前例子只为展示如何调用功能，故以下函数在运行时只能开其中一个
    # Waring: The following two commands can only choose one from the other

    # !! Waring: This function will send command to device
    # xhand_exam.exam_calibrate_joint_by_mold()

    # !! Waring: This function will send command to device
    # xhand_exam.exam_send_command()
    # time.sleep(1)

    # Close device (important)
    xhand_exam.set_hand_mode(mode=0)
    xhand_exam.exam_close_device()