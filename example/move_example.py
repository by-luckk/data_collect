'''运动相关的示例'''
import time
import math
# import setup_path
import platform

# 根据操作系统导入相应的模块
if platform.system() == 'Windows':
    from Release.windows import xCoreSDK_python
    from Release.windows.xCoreSDK_python.EventInfoKey import MoveExecution
elif platform.system() == 'Linux':
    from Release.linux import xCoreSDK_python
    from Release.linux.xCoreSDK_python.EventInfoKey import MoveExecution
else:
    raise ImportError("Unsupported operating system")
from log import print_log, print_separator
from datetime import timedelta
import cal_xyz_rpy as cal

import numpy as np

M_PI = math.pi

# Tfc = np.array([
#     [-0.19963129, -0.47027759,  0.85964314, -0.92384587],
#     [-0.43032947,  0.83024922,  0.35426372, -1.07684922],
#     [-0.88032034, -0.29920766, -0.36811803,  1.48577444],
#     [ 0.        ,  0.        ,  0.        ,  1.        ]
# ])

Tfc = np.array([
    [-1.0,  0.0,  0.0,  0.0],
    [ 0.0, -1.0,  0.0,  0.1],
    [ 0.0,  0.0,  1.0,  0.1],
    [ 0.0,  0.0,  0.0,  1.0]
])

matrix = np.array([
    [-0.186, -0.255, -0.949, 0.239],
    [0.185, -0.958, 0.221, 0.159],
    [-0.965, -0.134, 0.225, 0.347],
    [0.000, 0.000, 0.000, 1.000]
])


def move_op(robot, ec):
    pre_op(robot, ec)
    move_debug(robot, ec)


#最终运行版本需要
    # move_e_e2(robot, ec)
    # move_e2_e3(robot, ec)
    # move_e3_e4(robot, ec)

    # print_separator("move_op", length=110)
    
    # calcFk(robot, ec)
    # calcIk(robot, ec)
    # move_absJ(robot, ec)
    # moveL(robot, ec)
    # moveJ(robot, ec)
    # moveC(robot, ec)
    # moveCF(robot, ec)
    # moveSP(robot, ec)
    # moveWait(robot, ec)
    # pause_and_continue(robot, ec)
    # print_move_info(get_move_info(robot, ec))
    # query_controller_log(robot, ec)
    # robot.setNoneEventWatcher(xCoreSDK_python.Event.moveExecution,
    #                           ec)  # 结束时需要关闭监视器


def move_debug(robot, ec):

    '''获取当前笛卡尔坐标信息'''
    print_separator("get_cart_posture", length=80)
    cart_posture = robot.cartPosture(xCoreSDK_python.CoordinateType.endInRef,
                                     ec)
    print(f"trans,{','.join(map(str,cart_posture.trans))}")
    print(f"rpy,{','.join(map(str,cart_posture.rpy))}")

    pos_target =  cal.go_pose6_in_base(cart_posture.trans[0], cart_posture.trans[1], cart_posture.trans[2], cart_posture.rpy[0], cart_posture.rpy[1], cart_posture.rpy[2], Tfc,
                     matrix)
    


    print(f"pos_target: X={pos_target[0]:.3f}, Y={pos_target[1]:.3f}, Z={pos_target[2]:.3f}, "
          f"Roll={pos_target[3]:.3f}, Pitch={pos_target[4]:.3f}, Yaw={pos_target[5]:.3f}")
    yaw_angle = 90
    #固定姿态
    pos = [0.6, 0.13, 0.33]  # X, Y, Z (单位：mm)
    rpy_deg = [60.0, 0.0, yaw_angle]  # 依次为 Roll (A), Pitch (B), Yaw (C)
    rpy_rad = np.radians(rpy_deg)  # 角度转弧度
    # print(rpy_rad)  # 输出 [2.1344, -0.1801, 1.6012]

    # 创建新的 CartesianPosition
    cart_pos1 = xCoreSDK_python.CartesianPosition([
        pos[0], pos[1], pos[2],  # XYZ 位置
        rpy_rad[0], rpy_rad[1],rpy_rad[2]  # RPY 角度
    ])
    cart_pos = xCoreSDK_python.CartesianPosition(
        [0.7, 0.2, 0.516211, -1.57, 0, -1.57]) 

    movejcmd = xCoreSDK_python.MoveJCommand(cart_pos1, 1000, 10)
    cmdID = xCoreSDK_python.PyString()
    robot.moveAppend([movejcmd], cmdID, ec)  # [movelcmd]指令列表，可以添加多条指令，须为同类型指令
    print("Command ID:", cmdID.content())
    print_log("moveAppend", ec)
    robot.moveStart(ec)
    print_log("moveStart", ec)
    # Tbe = cal.euler_to_matrix
    # print_log("T=",str(np.array(Tbe)))
    wait_robot(robot, ec)



def pre_op(robot, ec):
    '''预操作'''
    print_separator("pre_op", length=80)
    # 切换到自动模式并上电
    robot.setOperateMode(xCoreSDK_python.OperateMode.manual, ec)
    print_log("setOperateMode", ec)
    robot.setPowerState(True, ec)
    print_log("setPowerState", ec)
    # 设置默认运动速度和转弯区
    robot.setMotionControlMode(
        xCoreSDK_python.MotionControlMode.NrtCommandMode, ec)
    print_log("setMotionControlMode", ec)
    set_default_zone(robot, ec)
    set_default_speed(robot, ec)
    # 可选：设置运动指令执行完成和错误信息回调
    robot.setEventWatcher(xCoreSDK_python.Event.moveExecution, print_move_info,
                          ec)


def set_default_zone(robot, ec):
    '''设置默认转弯区'''
    print_separator("set_default_zone", length=80)
    robot.setDefaultZone(50, ec)
    # 可选：设置默认转弯区
    print_log("setDefaultZone", ec)


def set_default_speed(robot, ec):
    '''设置默认速度'''
    print_separator("set_default_speed", length=80)
    robot.setDefaultSpeed(200, ec)
    # 可选：设置默认速度
    print_log("setDefaultSpeed", ec)


def calcFk(robot, ec):
    '''计算正解，关节角度->笛卡尔坐标'''
    print_separator("calcFk", length=80)
    start_angle = [0, 0.557737, -1.5184888, 0, -1.3036738, 0]  # 单位弧度
    robot_model = robot.model()
    toolset = xCoreSDK_python.Toolset()  #新建toolset
    cart_pose = robot_model.calcFk(start_angle, toolset, ec)
    print_log("calcFk", ec)
    print(f"elbow,{cart_pose.elbow}")
    print(f"hasElbow,{cart_pose.hasElbow}")
    print(f"confData,f{','.join(map(str,cart_pose.confData))}")
    print(f"external size,{len(cart_pose.external)}")
    print(f"trans,{','.join(map(str,cart_pose.trans))}")
    print(f"rpy,{','.join(map(str,cart_pose.rpy))}")
    print(f"pos,{','.join(map(str,cart_pose.pos))}")


def calcIk(robot, ec):
    '''计算逆解，笛卡尔坐标 -> 关节角度'''
    print_separator("calcIk", length=80)
    cart_pos = xCoreSDK_python.CartesianPosition(
        [0.60, 0.13, 0.41, -3.14, -0.23, -3.14])  #s4点位
    robot_model = robot.model()
    toolset = xCoreSDK_python.Toolset()  #新建toolset
    joint_pos = robot_model.calcIk(cart_pos, toolset, ec)
    print_log("calcIk", ec, ','.join(map(str, joint_pos)))


def move_absJ(robot, ec):
    '''moveAbsJ运动'''
    print_separator("move_absJ", length=80)
    joint_pos = xCoreSDK_python.JointPosition([1, 1, 1, 1, 1, 1])
    absjcmd = xCoreSDK_python.MoveAbsJCommand(joint_pos, 1000, 10)
    cmdID = xCoreSDK_python.PyString()
    robot.moveAppend([absjcmd], cmdID, ec)  # [absjcmd]指令列表，可以添加多条指令，须为同类型指令
    print("Command ID:", cmdID.content())
    print_log("moveAppend", ec)
    robot.moveStart(ec)
    print_log("moveStart", ec)
    wait_robot(robot, ec)


def moveL(robot, ec):

    # '''moveL运动'''
    # print_separator("moveL", length=80)
    # cart_pos = xCoreSDK_python.CartesianPosition(
    #     [0.614711, 0.136, 0.416211, -1.57, 0, -1.57])  #s4点位
    # movelcmd = xCoreSDK_python.MoveLCommand(cart_pos, 1000, 10)
    # cmdID = xCoreSDK_python.PyString()
    # robot.moveAppend([movelcmd], cmdID, ec)  # [movelcmd]指令列表，可以添加多条指令，须为同类型指令
    # print("Command ID:", cmdID.content())
    # print_log("moveAppend", ec)
    # robot.moveStart(ec)
    # print_log("moveStart", ec)
    # wait_robot(robot, ec)

    '''获取当前笛卡尔坐标信息'''
    print_separator("get_cart_posture", length=80)
    cart_posture = robot.cartPosture(xCoreSDK_python.CoordinateType.endInRef,
                                     ec)
    print(f"trans,{','.join(map(str,cart_posture.trans))}")
    print(f"rpy,{','.join(map(str,cart_posture.rpy))}")

    # 读取当前位置
    # 由于 cart_pos.trans 和 cart_pos.rpy 可能是 tuple，我们用 list 来修改
    int_trans = list(cart_posture.trans)
    int_rpy = list(cart_posture.rpy)
    # 修改位姿


    #初始姿态
    pos0 = [0.796, -0.102, 0.39]  # X, Y, Z (单位：mm)
    rpy_rad0 = [3, 0.22, -0.29]
    

    # rpy_deg = [137.685, -6.945, 94.7]  # 依次为 Roll (A), Pitch (B), Yaw (C)
    # rpy_rad0 = np.radians(rpy_deg)  # 角度转弧度



    # 创建新的 CartesianPosition
    cart_pos0 = xCoreSDK_python.CartesianPosition([
        pos0[0], pos0[1], pos0[2],  # XYZ 位置
        rpy_rad0[0], rpy_rad0[1],rpy_rad0[2]  # RPY 角度
    ])


    pos_target =  cal.go_pose6_in_base(cart_posture.trans[0], cart_posture.trans[1], cart_posture.trans[2], cart_posture.rpy[0], cart_posture.rpy[1], cart_posture.rpy[2], Tfc,
                     matrix)

    print(f"pos_target: X={pos_target[0]:.3f}, Y={pos_target[1]:.3f}, Z={pos_target[2]:.3f}, "
          f"Roll={pos_target[3]:.3f}, Pitch={pos_target[4]:.3f}, Yaw={pos_target[5]:.3f}")



    # 创建新的 CartesianPosition
    cart_pos_target = xCoreSDK_python.CartesianPosition([
        pos_target[0], pos_target[1], pos_target[2],  # XYZ 位置
        rpy_rad0[0], rpy_rad0[1],rpy_rad0[2]  # RPY 角度
    ])

    # 创建新的 CartesianPosition
    cart_pos1 = xCoreSDK_python.CartesianPosition([
        pos[0], pos[1], pos[2],  # XYZ 位置
        rpy_rad[0], rpy_rad[1],rpy_rad[2]  # RPY 角度
    ])

    movelcmd = xCoreSDK_python.MoveJCommand(cart_pos0, 1000, 10)
    cmdID = xCoreSDK_python.PyString()
    robot.moveAppend([movelcmd], cmdID, ec)  # [movelcmd]指令列表，可以添加多条指令，须为同类型指令
    print("Command ID:", cmdID.content())
    print_log("moveAppend", ec)
    robot.moveStart(ec)
    print_log("moveStart", ec)
    # Tbe = cal.euler_to_matrix
    # print_log("T=",str(np.array(Tbe)))
    wait_robot(robot, ec)




def moveJ(robot, ec):
    '''moveJ运动'''
    print_separator("moveJ", length=80)
    cart_pos = xCoreSDK_python.CartesianPosition(
        [0.614711, 0.136, 0.416211, -M_PI, 0, -M_PI])  #s4点位
    movejcmd = xCoreSDK_python.MoveJCommand(cart_pos, 1000, 10)
    cmdID = xCoreSDK_python.PyString()
    robot.moveAppend([movejcmd], cmdID, ec)  # [movejcmd]指令列表，可以添加多条指令，须为同类型指令
    print("Command ID:", cmdID.content())
    print_log("moveAppend", ec)
    robot.moveStart(ec)
    print_log("moveStart", ec)
    wait_robot(robot, ec)


def moveC(robot, ec):
    '''moveC运动'''
    print_separator("moveC", length=80)
    target = xCoreSDK_python.CartesianPosition(
        [0.214711, 0.236, 0.616211, -M_PI, 0, -M_PI])  #s4点位
    aux = xCoreSDK_python.CartesianPosition(
        [0.414711, 0.236, 0.416211, -M_PI, 0, -M_PI])  #s4点位
    moveccmd = xCoreSDK_python.MoveCCommand(target, aux, 1000, 10)
    cmdID = xCoreSDK_python.PyString()
    robot.moveAppend([moveccmd], cmdID, ec)
    print("Command ID:", cmdID.content())
    print_log("moveAppend", ec)
    robot.moveStart(ec)
    print_log("moveStart", ec)
    wait_robot(robot, ec)


def moveCF(robot, ec):
    '''moveCF运动'''
    print_separator("moveCF", length=80)
    target = xCoreSDK_python.CartesianPosition(
        [0.614711, 0.136, 0.416211, -1.57, 0, -1.57])  #s4点位
    aux = xCoreSDK_python.CartesianPosition(
        [0.614711, 0.236, 0.416211, -1.57, 0, -1.57])  #s4点位
    movecf_cmd = xCoreSDK_python.MoveCFCommand(target, aux, 2, 1000, 10)
    cmdID = xCoreSDK_python.PyString()
    robot.moveAppend([movecf_cmd], cmdID, ec)
    print("Command ID:", cmdID.content())
    print_log("moveAppend", ec)
    robot.moveStart(ec)
    print_log("moveStart", ec)
    wait_robot(robot, ec)


def moveSP(robot, ec):
    '''moveSP运动'''
    print_separator("moveSP", length=80)
    target = xCoreSDK_python.CartesianPosition(
        [0.214711, 0.136, 0.416211, -M_PI, 0, -M_PI])  #s4点位
    r0 = 0.1
    rstep = 0.05
    angle = 1
    dir = True
    movesp_cmd = xCoreSDK_python.MoveSPCommand(target, r0, rstep, angle, dir,
                                               1000)
    cmdID = xCoreSDK_python.PyString()
    robot.moveAppend([movesp_cmd], cmdID, ec)
    print("Command ID:", cmdID.content())
    print_log("moveAppend", ec)
    robot.moveStart(ec)
    print_log("moveStart", ec)
    wait_robot(robot, ec)


def moveWait(robot, ec):
    '''moveWait等待'''
    print_separator("moveWait", length=80)
    robot.stop(ec)
    robot.moveReset(ec)
    joint_pos1 = xCoreSDK_python.JointPosition([0, 0, 0, 0, 0, 0])
    absjcmd1 = xCoreSDK_python.MoveAbsJCommand(joint_pos1, 1000, 10)
    joint_pos2 = xCoreSDK_python.JointPosition([1, 1, 1, 1, 1, 1])
    absjcmd2 = xCoreSDK_python.MoveAbsJCommand(joint_pos2, 1000, 10)

    cmdID = xCoreSDK_python.PyString()
    robot.moveAppend([absjcmd1], cmdID, ec)
    print("Command ID:", cmdID.content())
    print_log("moveAppend", ec)
    robot.moveStart(ec)
    print_log("moveStart", ec)

    # delay = timedelta(seconds=2)  # 延时两秒
    delay = timedelta(milliseconds=500)  # 延时500毫秒
    mwait = xCoreSDK_python.MoveWaitCommand(delay)
    robot.moveAppend(mwait, cmdID, ec)  # moveAppend使用moveWait指令时没有列表的形式
    print_log("moveAppend", ec)

    robot.moveAppend([absjcmd2], cmdID, ec)
    print("Command ID:", cmdID.content())
    print_log("moveAppend", ec)
    robot.moveStart(ec)
    print_log("moveStart", ec)
    wait_robot(robot, ec)


def wait_robot(robot, ec):
    '''等待运动结束 - 通过查询机械臂是否处于运动中的方式'''
    print_separator("wait_robot", length=80)
    running = True
    while (running):
        time.sleep(0.1)
        st = robot.operationState(ec)
        if (st == xCoreSDK_python.OperationState.idle
                or st == xCoreSDK_python.OperationState.unknown):
            running = False
    print("move finished")


def pause_and_continue(robot, ec):
    '''暂停和继续'''
    print_separator("pause and continue", length=80)
    joint_pos = xCoreSDK_python.JointPosition([1, 1, 1, 1, 1, 1])
    absjcmd = xCoreSDK_python.MoveAbsJCommand(joint_pos, 1000, 10)
    cmdID = xCoreSDK_python.PyString()
    robot.moveAppend([absjcmd], cmdID, ec)  # [absjcmd]指令列表，可以添加多条指令，须为同类型指令
    print_log("moveAppend", ec)
    robot.moveStart(ec)
    print("start")
    time.sleep(2)  # 等待2秒后暂停
    robot.stop(ec)
    print("pause")
    time.sleep(2)  # 等待2秒后继续
    robot.moveStart(ec)
    print("continue")
    time.sleep(2)  # 等待2秒后结束
    robot.stop(ec)
    print("stop")


def query_controller_log(robot, ec):
    '''查询控制器日志'''
    print_separator("query controller log", length=80)
    # 查询最近5条错误级别控制器日志
    controller_logs = robot.queryControllerLog(
        5, {xCoreSDK_python.LogInfoLevel.error}, ec)
    print_log("queryControllerLog", ec)
    for log in controller_logs:
        print(log.content)


def get_move_info(robot, ec):
    '''获取运动信息'''
    print_separator("get move info", length=80)
    info = robot.queryEventInfo(xCoreSDK_python.Event.moveExecution, ec)
    print_log("queryEventInfo", ec)
    return info


def print_move_info(info: dict):
    '''打印运动执行信息'''
    print_separator("print move info", length=80)
    print(f"{MoveExecution.ID}:{info[MoveExecution.ID]}")
    print(f"{MoveExecution.ReachTarget}:{info[MoveExecution.ReachTarget]}")
    print(f"{MoveExecution.WaypointIndex}:{info[MoveExecution.WaypointIndex]}")
    print(f"{MoveExecution.Error}:{info[MoveExecution.Error]}")
    print(f"{MoveExecution.Remark}:{info[MoveExecution.Remark]}")


def main():
    try:
        ip = "192.168.2.160"
        robot = xCoreSDK_python.xMateRobot(ip)
        ec = {}
        move_op(robot, ec)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
