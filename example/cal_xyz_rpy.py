import numpy as np
from scipy.spatial.transform import Rotation as R


def euler_to_matrix(x, y, z, roll, pitch, yaw):
    """
    将位移和欧拉角（XYZ 顺序）转换为 4x4 的齐次变换矩阵。

    参数:
        x, y, z (float): 位移（单位：米）。
        roll, pitch, yaw (float): 欧拉角（单位：弧度，XYZ 顺序）。

    返回:
        np.array: 4x4 的齐次变换矩阵。
    """
    # 计算旋转矩阵（XYZ 顺序）
    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(roll), -np.sin(roll)],
        [0, np.sin(roll), np.cos(roll)]
    ])

    Ry = np.array([
        [np.cos(pitch), 0, np.sin(pitch)],
        [0, 1, 0],
        [-np.sin(pitch), 0, np.cos(pitch)]
    ])

    Rz = np.array([
        [np.cos(yaw), -np.sin(yaw), 0],
        [np.sin(yaw), np.cos(yaw), 0],
        [0, 0, 1]
    ])

    # 组合旋转矩阵（R = Rz * Ry * Rx）
    R = Rz @ Ry @ Rx

    # 构造齐次变换矩阵
    T = np.eye(4)
    T[:3, :3] = R  # 旋转部分
    T[:3, 3] = [x, y, z]  # 平移部分

    return T


def transform_to_xyz_rpy(matrix):
    """
    将 4x4 的齐次变换矩阵转换为位移和欧拉角（XYZ 顺序）。

    参数:
        matrix (np.array): 4x4 的齐次变换矩阵。

    返回:
        tuple: (x, y, z, roll, pitch, yaw) 位移和欧拉角。
    """
    # 提取位移 (x, y, z)
    x, y, z = matrix[:3, 3]

    # 提取旋转部分 (左上角 3x3 子矩阵)
    R = matrix[:3, :3]

    # 计算欧拉角（XYZ 顺序）
    # Roll (绕 X 轴旋转)
    roll = np.arctan2(R[2, 1], R[2, 2])
    # Pitch (绕 Y 轴旋转)
    pitch = np.arctan2(-R[2, 0], np.sqrt(R[2, 1] ** 2 + R[2, 2] ** 2))
    # Yaw (绕 Z 轴旋转)
    yaw = np.arctan2(R[1, 0], R[0, 0])

    return x, y, z, roll, pitch, yaw



# 这，是这个机械臂，在端口朝向x正方向的时候，debug阶段，参考欧拉角度，所需要的函数
def effect_euler_transformation(euler_angles):
    """
    输入欧拉角列表！ (roll, pitch, yaw) ，返回变换后的欧拉角。
    :param euler_angles: 输入欧拉角 [roll, pitch, yaw]（单位：弧度）
    :return: 变换后的欧拉角 [roll2, pitch2, yaw2]（单位：弧度）
    """
    R10 = np.array([[0, 0, 1],
                    [1, 0, 0],
                    [0, 1, 0]]) 
    # 将欧拉角转换为旋转矩阵 R0x
    R0x = R.from_euler('xyz', euler_angles).as_matrix()

    # 计算 R1x = R10 @ R0x
    R1x = R10 @ R0x

    # 将旋转矩阵转换回欧拉角
    R1x_euler_effect = R.from_matrix(R1x).as_euler('xyz')

    return R1x_euler_effect



def go_pose6_in_base(x, y, z, roll, pitch, yaw, Tfc, Foundation_Pose_Matrix):
    Tbf = euler_to_matrix(x, y, z, roll, pitch, yaw)
    Tct = Foundation_Pose_Matrix
    Tbc = Tbf @ Tfc
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
    x2, y2, z2, roll2, pitch2, yaw2 = transform_to_xyz_rpy(Tbf2)
    return x2, y2, z2, roll2, pitch2, yaw2

