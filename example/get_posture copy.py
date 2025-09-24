import setup_path
import platform
import os
import math
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

# ---------- 辅助函数：状态判定 & 规范化 ----------

def is_ok(ec):
    """兼容 str/int/dict/对象 的成功判定。"""
    if ec is None or ec == {} or ec == []:
        return True

    if isinstance(ec, (int, float)):
        return int(ec) == 0

    if isinstance(ec, str):
        return ec.strip() in ("操作成功完成", "成功", "OK", "Ok", "ok", "Success", "success", "Succeeded")

    if isinstance(ec, dict):
        for k in ("code", "errCode", "error_code"):
            if k in ec:
                try:
                    return int(ec[k]) == 0
                except Exception:
                    pass
        msg = str(ec.get("msg", "")).strip()
        if msg in ("操作成功完成", "成功", "OK", "Ok", "ok", "Success", "success", "Succeeded"):
            return True
        if "error" in ec and hasattr(xCoreSDK_python, "ErrorCode") and hasattr(xCoreSDK_python.ErrorCode, "success"):
            return ec["error"] == xCoreSDK_python.ErrorCode.success
        return False

    for attr in ("code", "errCode", "error_code"):
        if hasattr(ec, attr):
            try:
                return int(getattr(ec, attr)) == 0
            except Exception:
                pass
    if hasattr(ec, "msg"):
        if str(getattr(ec, "msg")).strip() in ("操作成功完成", "成功", "OK", "Ok", "ok", "Success", "success", "Succeeded"):
            return True

    return False


def normalize_ec(ec):
    """把 ec 统一成 {'code': int或None, 'msg': str}，便于日志展示。"""
    if ec is None:
        return {'code': 0, 'msg': ''}
    if isinstance(ec, (int, float)):
        return {'code': int(ec), 'msg': ''}
    if isinstance(ec, str):
        return {
            'code': 0 if ec.strip() in ("操作成功完成", "成功", "OK", "Success", "ok", "success") else None,
            'msg': ec
        }
    if isinstance(ec, dict):
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
    # 其他对象：尽量读属性
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

# ---------- 对原有 print_log 的“防炸壳”包装 ----------

def safe_print_log(tag, ec=None, extra=""):
    """
    始终把 ec 规范化后再交给 print_log；
    一旦 print_log 内部因为把字符串当 dict 索引而抛错，自动降级到 print。
    """
    ec_norm = normalize_ec(ec)
    try:
        # 兼容不同的 print_log 签名：常见的两种 (tag, ec) / (tag, ec, extra)
        # 如果你的 print_log 只有两个参数，下面这行会抛 TypeError，我们再降级尝试两参调用。
        print_log(tag, ec_norm, extra)
    except TypeError:
        try:
            print_log(tag, ec_norm)
        except Exception as e:
            print(f"[print_log fallback] {tag} | ec={ec_norm} | extra={extra} | reason={e}")
    except Exception as e:
        print(f"[print_log fallback] {tag} | ec={ec_norm} | extra={extra} | reason={e}")

# ---------- 业务函数 ----------

def get_posture(robot, ec):
    print_separator("get_posture", length=80)

    # 调用 SDK
    pos = robot.posture(xCoreSDK_python.CoordinateType.flangeInBase, ec)

    # 统一日志
    safe_print_log("ec(type)", ec, type(ec).__name__)
    safe_print_log("ec(raw)", ec, repr(ec))

    # 成功/失败判断
    if not is_ok(ec):
        safe_print_log("获取位姿失败", ec)
        return

    # 成功：打印位姿
    safe_print_log("posture", ec, ', '.join(map(str, pos)))

    # 解析与单位转换
    x, y, z = pos[:3]
    a, b, c = pos[3:]             # 弧度
    a = a * 180 / math.pi
    b = b * 180 / math.pi
    c = c * 180 / math.pi

    x, y, z = x * 1000, y * 1000, z * 1000  # 米→毫米
    pose_str = f"{x:.3g}, {y:.3g}, {z:.3g}, {a:.3g}, {b:.3g}, {c:.3g}\n"
    print(pose_str)

    # 保存
    os.makedirs(os.path.dirname(POSES_FILE_PATH), exist_ok=True)
    with open(POSES_FILE_PATH, "a") as f:
        f.write(pose_str)

    safe_print_log(f"机械臂位姿已保存到 {POSES_FILE_PATH}", ec)


if __name__ == "__main__":
    try:
        # 连接机器人
        ip = "192.168.2.160"
        robot = xCoreSDK_python.xMateRobot(ip)  # 若报类名不存在，用 dir(xCoreSDK_python) 查真实类名
        # 如果 SDK 有内置错误对象类型，优先用：
        # ec = xCoreSDK_python.Error() if hasattr(xCoreSDK_python, "Error") else {}
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

