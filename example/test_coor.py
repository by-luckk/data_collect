import numpy as np
import setup_path
import platform
import os
import cal_xyz_rpy as cal

# 根据操作系统导入相应的模块
if platform.system() == 'Windows':
    from Release.windows import xCoreSDK_python
elif platform.system() == 'Linux':
    from Release.linux import xCoreSDK_python
else:
    raise ImportError("Unsupported operating system")

from log import print_log, print_separator



Foundation_Pose_Matrix = np.array([[-0.417, 0.238, -0.877, 0.296],
                                    [-0.243, -0.959, -0.145, 0.185],
                                    [-0.876, 0.153, 0.458, 0.452],
                                    [0.000, 0.000, 0.000, 1.000]])

Tfc = np.array([[-1,0,0,0.020],
                 [0,1,0,0.084],
                 [0,0,-1,0.07],
                 [0,0,0,1]])


def get_posture_T(robot, ec):
    pos = robot.posture(xCoreSDK_python.CoordinateType.flangeInBase, ec)
    x = pos[0]
    y = pos[1]
    z = pos[2]
    roll = pos[3]
    pitch = pos[4]
    yaw = pos[5]
    Tbf = cal.euler_to_matrix(x, y, z, roll, pitch, yaw)
    return Tbf

def go_to_pose(robot, ec):
    Tbf = get_posture_T(robot, ec)
    Tct = Foundation_Pose_Matrix
    # Tbc = Tbf @ Tfc
    Tc2t = np.array([
        [0, 0, -1, 0],
        [0, -1, 0, 0],
        [-1, 0, 0, 0.35],
        [0, 0, 0, 1]
    ])
    Ttc2 = np.linalg.inv(Tc2t)
    # Tbc2 = Tbf @ Tfc @ Tct @ Ttc2
    Tcf = np.linalg.inv(Tfc)
    Tbf2 = Tbf @ Tfc @ Tct @ Ttc2 @ Tcf
    x2, y2, z2, roll2, pitch2, yaw2 = cal.transform_to_xyz_rpy(Tbf2)
    Tff2 = np.linalg.inv(Tbf) @ Tbf2
    dx, dy, dz, dr, dp, dyaw = cal.transform_to_xyz_rpy(Tff2)

    # 打印到一行，保留三个有效数字
    print(f"目标绝对位置:  x2: {x2:.3g}, y2: {y2:.3g}, z2: {z2:.3g}, roll2: {roll2:.3g}, pitch2: {pitch2:.3g}, yaw2: {yaw2:.3g}\n")
    print(f"以第一个法兰为作弊阿西，变化如下: \n dx: {dx:.3g}, dy: {dy:.3g}, dz: {dz:.3g}, dr: {dr:.3g}, dp: {dp:.3g}, dyaw: {dyaw:.3g}\n")


if __name__ == "__main__":
    try:
        # 连接机器人
        ip = "192.168.2.160"
        robot = xCoreSDK_python.xMateRobot(ip)
        ec = {}

        # 采集机械臂位姿
        get_posture_T(robot, ec)

        # 运算得到机械臂末端的目标位姿


    except Exception as e:
        print(f"An error occurred: {e}")
