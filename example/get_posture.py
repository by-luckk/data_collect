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

# 目标存储路径（手眼标定工程的数据文件）
POSES_FILE_PATH = r"data/arm_poses1.txt"
# POSES_FILE_PATH = r"D:\Users\10029\Desktop\hand_eye_calibration\data\x_yarm_poses.txt"

import math

def is_ok(ec):
    # 空、None 都视为成功
    if ec is None or ec == {} or ec == []:
        return True

    # 数字：0 成功
    if isinstance(ec, (int, float)):
        return int(ec) == 0

    # 字符串：匹配常见“成功”文案
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


def normalize_ec(ec):
    # 统一转成 {'code': int或None, 'msg': str} 的格式
    if ec is None:
        return {'code': 0, 'msg': ''}
    if isinstance(ec, (int, float)):
        return {'code': int(ec), 'msg': ''}
    if isinstance(ec, str):
        # 这版 SDK 成功是“操作成功完成”
        return {'code': 0 if ec.strip() in ("操作成功完成", "成功", "OK", "Success", "ok", "success") else None,
                'msg': ec}
    if isinstance(ec, dict):
        # 补齐缺失字段
        code = None
        for k in ("code", "errCode", "error_code"):
            if k in ec:
                try:
                    code = int(ec[k])
                except Exception:
                    code = None
                break
        msg = str(ec.get("msg", "")) if hasattr(ec, "get") else ""
        return {'code': code, 'msg': msg}
    # 其他对象，尽量读属性
    code = None
    for attr in ("code", "errCode", "error_code"):
        if hasattr(ec, attr):
            try:
                code = int(getattr(ec, attr))
            except Exception:
                code = None
            break
    msg = str(getattr(ec, "msg", ""))
    return {'code': code, 'msg': msg}



def get_posture(robot, ec):
    print_separator("get_posture", length=80)

    pos = robot.posture(xCoreSDK_python.CoordinateType.flangeInBase, ec)

    # 建议先看类型，便于以后定规则
    print_log("ec(type)", type(ec).__name__)
    print_log("ec", repr(ec))  # 用 repr 看原始值

    if not is_ok(ec):
        print_log("获取位姿失败", ec)
        return

    print_log("posture", ec, ', '.join(map(str, pos)))

    x, y, z = pos[:3]
    a, b, c = pos[3:]             # 弧度
    a = a * 180 / math.pi
    b = b * 180 / math.pi
    c = c * 180 / math.pi

    x, y, z = x * 1000, y * 1000, z * 1000  # 米→毫米
    pose_str = f"{x:.3g}, {y:.3g}, {z:.3g}, {a:.3g}, {b:.3g}, {c:.3g}\n"
    print(pose_str)

    os.makedirs(os.path.dirname(POSES_FILE_PATH), exist_ok=True)
    with open(POSES_FILE_PATH, "a") as f:
        f.write(pose_str)

    print_log("ec(type)", None, type(ec).__name__)
    print_log("ec", normalize_ec(ec), repr(ec))

    if not is_ok(ec):
        print_log("获取位姿失败", normalize_ec(ec))
        return

    print_log("posture", normalize_ec(ec), ', '.join(map(str, pos)))



if __name__ == "__main__":
    try:
        # 连接机器人
        ip = "192.168.2.160"
        robot = xCoreSDK_python.xMateRobot(ip)
        ec = {}

        # 采集机械臂位姿
        get_posture(robot, ec)

    except Exception as e:
        print(f"An error occurred: {e}")





# def get_posture_T(robot, ec):
#     pos = robot.posture(xCoreSDK_python.CoordinateType.flangeInBase, ec)
#     x = pos[0]
#     y = pos[1]
#     z = pos[2]
#     roll = pos[3]
#     pitch = pos[4]
#     yaw = pos[5]
#     Tbf = cal.euler_to_matrix(x, y, z, roll, pitch, yaw)
#     return Tbf

# def get_posture(robot, ec):
#     """获取当前机械臂末端法兰位姿，并存入 arm_poses.txt"""
#     print_separator("get_posture", length=80)

#     # 获取机械臂位姿
#     pos = robot.posture(xCoreSDK_python.CoordinateType.flangeInBase, ec)

#     if ec:
#         print_log("获取位姿失败", ec)
#         return

#     print_log("posture", ec, ', '.join(map(str, pos)))

#     # 解析数据
#     x, y, z = pos[:3]  # 平移量 (单位：米)
#     a, b, c = pos[3:]  # 旋转量 (单位：弧度)
#     a = a * 180 / 3.14159
#     b = b * 180 / 3.14159
#     c = c * 180 / 3.14159

#     # 转换单位：米 -> 毫米
#     x, y, z = x * 1000, y * 1000, z * 1000

#     # 组织数据格式
#     # pose_str = f"{x:.6f}, {y:.6f}, {z:.6f}, {a:.6f}, {b:.6f}, {c:.6f}\n"
#     pose_str = f"{x:.3g}, {y:.3g}, {z:.3g}, {a:.3g}, {b:.3g}, {c:.3g}\n"

#     print(pose_str)
#     # 确保目录存在
#     os.makedirs(os.path.dirname(POSES_FILE_PATH), exist_ok=True)

#     # 追加写入到 arm_poses.txt
#     with open(POSES_FILE_PATH, "a") as f:
#         f.write(pose_str)

#     print_log(f"机械臂位姿已保存到 {POSES_FILE_PATH}")

