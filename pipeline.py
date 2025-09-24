# from realsense_wzr import send_image_to_server
import math
import platform
import numpy as np
import time
import sys
sys.path.append('/home/slam/Desktop/tactile')  # Windows

# 根据操作系统导入相应的模块
if platform.system() == 'Windows':
    from Release.windows import xCoreSDK_python
elif platform.system() == 'Linux':
    from Release.linux import xCoreSDK_python
else:
    raise ImportError("Unsupported operating system")
from example.log import print_log
from example.move_example import wait_robot
import xhand_usr_control

from example.matrix_trans import *
from scipy.spatial.transform import Rotation as R
# [x, y, z, pitch, roll, yaw]
pose_init = [0.5, 0.05, 0.4, math.radians(90), math.radians(-90), math.radians(90)]
pose_grasp = pose_init.copy()
pose_grasp[2] = 0.07
# pose_grasp[2] = 0.2

ip = "192.168.2.160"
robot = xCoreSDK_python.xMateRobot(ip) 
ec = {}


# 力控类
fc = robot.forceControl()

# 上电
robot.setOperateMode(xCoreSDK_python.OperateMode.automatic, ec)
robot.setPowerState(True, ec)
process = xhand_usr_control.xhand_usr_init()  

# 创建 Tool
tool = xCoreSDK_python.Toolset()

tool.end = xCoreSDK_python.Frame(trans=[0, 0, 0], rpy=[0, 0, 0]) 
# tool.load = xCoreSDK_python.Load(2.67, [0.0127, -0.0316, 0.1033],[0.001, 0.001, 0.001])      # 工具质量0.8kg，质心偏移

# 设置参考坐标系绕 Z 轴旋转
tool.ref.trans = [0.0, 0.0, 0.0]  # 原点不变
tool.ref.rpy = [0.0, 0.0, math.radians(135)]  # 绕 Z 轴旋转

# 设置 toolset 到机器人
robot.setToolset(tool, ec)

def move_to_point(robot, ec, name, pos, vel, method):
    cart_pose = xCoreSDK_python.CartesianPosition(pos)
    if method == "moveJ":
        movelcmd = xCoreSDK_python.MoveJCommand(cart_pose, vel, 10)
    elif method == "moveL":
        movelcmd = xCoreSDK_python.MoveLCommand(cart_pose, vel, 10)
    elif method == "moveC":
        movelcmd = xCoreSDK_python.MoveCCommand(cart_pose, vel, 10)
    else:
        print("move_to_point: method error")
        return


    cmdID = xCoreSDK_python.PyString()
    robot.moveAppend([movelcmd], cmdID, ec)  # [movelcmd]指令列表，可以添加多条指令，须为同类型指令
    print("Command ID:", cmdID.content())
    print_log("moveAppend", ec)
    robot.moveStart(ec)
    print_log("moveStart", ec)
    print(name)
    wait_robot(robot, ec)
def press_enter_for_next_step():
    while True:
        user_input = input("按回车进入下一步：")
        if user_input == "":
            break
        else:
            print(f"You entered: {user_input}")

def main():
    try:      
        xhand_usr_control.xhand_usr_control(process,control_order=1)
        time.sleep(0.5)
        move_to_point(robot, ec, "init", pose_init, 300, "moveJ")
        move_to_point(robot, ec, "grasp", pose_grasp, 300, "moveJ")
        xhand_usr_control.xhand_usr_control(process,control_order=0)
        press_enter_for_next_step()
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == '__main__':
    main()


