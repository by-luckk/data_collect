# get_posture_min.py
import os, sys, math, platform, traceback

# === 1) 放回 setup_path（它会把项目根与 Release/* 加进 sys.path） ===
try:
    import setup_path  # 在 example/ 目录下，这个导入会成功并修改 sys.path
except Exception:
    pass

# === 2) 再做一层兜底：手动把候选路径塞进 sys.path（防止 setup_path 没生效） ===
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
CANDIDATES = [
    ROOT,
    os.path.join(ROOT, "Release"),
    os.path.join(ROOT, "Release", "linux"),
    os.path.join(ROOT, "Release", "windows"),
]
for p in CANDIDATES:
    if p not in sys.path:
        sys.path.insert(0, p)

# === 3) 导入 SDK 扩展 ===
if platform.system() == "Windows":
    from Release.windows import xCoreSDK_python
elif platform.system() == "Linux":
    from Release.linux import xCoreSDK_python
else:
    raise ImportError("Unsupported operating system")

POSES_FILE_PATH = "data/arm_poses1.txt"

def resolve_coord_type():
    ct = xCoreSDK_python.CoordinateType
    for name in ("flangeInBase", "FlangeInBase", "FLANGE_IN_BASE", "flange_in_base"):
        if hasattr(ct, name):
            return getattr(ct, name)
    raise AttributeError("CoordinateType 里找不到法兰到基坐标的枚举；请先 print(dir(xCoreSDK_python.CoordinateType)) 查看真实名字。")

def is_ok(ec):
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
        return msg in ("操作成功完成", "成功", "OK", "Ok", "ok", "Success", "success", "Succeeded")
    for attr in ("code", "errCode", "error_code"):
        if hasattr(ec, attr):
            try:
                return int(getattr(ec, attr)) == 0
            except Exception:
                pass
    if hasattr(ec, "msg"):
        return str(getattr(ec, "msg")).strip() in ("操作成功完成", "成功", "OK", "Ok", "ok", "Success", "success", "Succeeded")
    return False

def save_pose(pos):
    x, y, z = pos[:3]
    a, b, c = pos[3:]                 # 弧度
    a, b, c = a*180/math.pi, b*180/math.pi, c*180/math.pi
    x, y, z = x*1000, y*1000, z*1000  # 米→毫米
    pose_str = f"{x:.3g}, {y:.3g}, {z:.3g}, {a:.3g}, {b:.3g}, {c:.3g}\n"
    print("[POSE]", pose_str.strip())
    os.makedirs(os.path.dirname(POSES_FILE_PATH), exist_ok=True)
    with open(POSES_FILE_PATH, "a") as f:
        f.write(pose_str)
    print(f"[INFO] 机械臂位姿已保存到 {POSES_FILE_PATH}")

def main():
    print("-"*34 + " get_posture (minimal) " + "-"*34)
    ip = "192.168.2.160"

    # 兼容不同版本的类名
    robot_cls = None
    for name in ("xMateRobot", "Robot", "xMate3Robot", "xMate3ProRobot"):
        if hasattr(xCoreSDK_python, name):
            robot_cls = getattr(xCoreSDK_python, name)
            break
    if robot_cls is None:
        raise AttributeError("在 xCoreSDK_python 中找不到 Robot 类，请先 print(dir(xCoreSDK_python)) 确认类名。")

    robot = robot_cls(ip)
    ec = xCoreSDK_python.Error() if hasattr(xCoreSDK_python, "Error") else {}

    coord = resolve_coord_type()

    try:
        pos = robot.posture(coord, ec)

        print(f"[DEBUG] SDK .so: {getattr(xCoreSDK_python, '__file__', '(built-in)')}")
        print(f"[DEBUG] ec type: {type(ec).__name__}")
        print(f"[DEBUG] ec repr: {repr(ec)}")
        print(f"[DEBUG] pos type: {type(pos).__name__}")
        print(f"[DEBUG] pos repr: {repr(pos)}")

        if not isinstance(pos, (list, tuple)) or len(pos) < 6:
            print("[WARN] posture 返回的 pos 不是 6 维向量，上述 [DEBUG] 已打印其内容，请检查接口/版本。")
            return

        if not is_ok(ec):
            print("[ERROR] SDK 返回非成功状态，上述 [DEBUG] 已打印 ec 原始内容。")
            return

        save_pose(pos)

    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    main()
