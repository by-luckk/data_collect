import time
import setup_path
import platform

# 根据操作系统导入相应的模块
if platform.system() == 'Windows':
    from Release.windows import xCoreSDK_python
elif platform.system() == 'Linux':
    from Release.linux import xCoreSDK_python
else:
    raise ImportError("Unsupported operating system")

from log import print_log, print_separator
from move_example import wait_robot


def drag_op(robot, ec):
    print_separator("drag_op", length=110)

    # 手动模式 + ↓ 下电（很关键）
    robot.setOperateMode(xCoreSDK_python.OperateMode.manual, ec)
    print_log("setOperateMode(manual)", ec)
    robot.setPowerState(False, ec)   # 必须下电，才能进入拖拽
    print_log("setPowerState(False)", ec)

    robot.moveReset(ec)
    print_log("moveReset", ec)

    while True:
        cmd = input(
            "d: enable drag, k: disable drag,\n"
            "a: start record, b: stop record,\n"
            "s: save record path, c: cancel record,\n"
            "u: query path lists, v: delete path,\n"
            "p: replay specific path, q: exit\n> "
        ).strip().lower()
        try:
            if cmd == 'd':
                open_drag(robot, ec)
            elif cmd == 'k':
                close_drag(robot, ec)
            # ... 省略其余分支 ...
        except Exception as e:
            print(f"[ERROR] {e}")

    # 退出前：保证禁用拖拽并下电（或按你需要上电）
    try:
        robot.disableDrag(ec)
    except Exception:
        pass
    robot.setPowerState(False, ec)
    print_log("setPowerState(False)", ec)


def open_drag(robot, ec):
    """打开拖动（要求：手动模式 + 下电）"""
    # 如果你担心当前不是下电状态，可以显式再下电一次：
    # robot.setPowerState(False, ec)

    # 正确签名：enableDrag(space:int, type:int, ec:dict, enable_drag_button:bool)
    robot.enableDrag(1, 2, ec, True)
    print_log("enableDrag(space=1,type=2,button=True)", ec)


def close_drag(robot, ec):
    """关闭拖动（之后一般需要上电才能执行运动）"""
    robot.disableDrag(ec)
    print_log("disableDrag", ec)

    # 关闭拖拽后，如果你要录制/回放或关节运动，需要上电
    robot.setPowerState(True, ec)
    print_log("setPowerState(True)", ec)


def start_record_path(robot, ec):
    """开始录制路径"""
    robot.startRecordPath(10, ec)
    print_log("startRecordPath(window=10)", ec)

def stop_record_path(robot, ec):
    """停止录制路径"""
    robot.stopRecordPath(ec)
    print_log("stopRecordPath", ec)

def save_record_path(robot, ec):
    """保存录制路径"""
    path_name = input("input path name: ").strip()
    robot.saveRecordPath(path_name, ec)
    print_log(f"saveRecordPath({path_name})", ec)

def cancel_record_path(robot, ec):
    """取消录制路径"""
    robot.cancelRecordPath(ec)
    print_log("cancelRecordPath", ec)

def query_path_lists(robot, ec):
    """查询路径列表"""
    lists = robot.queryPathLists(ec)
    print_log("queryPathLists", ec)
    print(lists)

def delete_path(robot, ec):
    """删除路径"""
    path_name = input("input delete path name: ").strip()
    robot.removePath(path_name, ec)
    print_log(f"removePath({path_name})", ec)

def replay_path(robot, ec):
    """路径回放"""
    name = input("input replay path name: ").strip()
    # 回放前要关闭拖拽，并切自动 + 上电
    robot.disableDrag(ec)
    print_log("disableDrag(before replay)", ec)
    robot.setOperateMode(xCoreSDK_python.OperateMode.automatic, ec)
    print_log("setOperateMode(automatic)", ec)
    robot.setPowerState(True, ec)
    print_log("setPowerState(True)", ec)
    robot.replayPath(name, 1, ec)  # 1 表示回放一次（按你的原代码）
    print_log(f"replayPath({name}, count=1)", ec)
    # 回放后可切回手动
    robot.setOperateMode(xCoreSDK_python.OperateMode.manual, ec)
    print_log("setOperateMode(manual, after replay)", ec)

if __name__ == "__main__":
    try:
        ip = "192.168.2.160"
        robot = xCoreSDK_python.xMateRobot(ip)
        # 建议用 SDK 的错误对象（如果有）
        ec = xCoreSDK_python.Error() if hasattr(xCoreSDK_python, "Error") else {}
        drag_op(robot, ec)
    except Exception as e:
        print(f"An error occurred: {e}")
