"""最小运行程序，使用moveL或moveJ将机器人移动到指定点位"""

import setup_path
import platform

# 根据操作系统导入相应的模块
if platform.system() == 'Windows':
    from Release.windows import xCoreSDK_python
elif platform.system() == 'Linux':
    from Release.linux import xCoreSDK_python
else:
    raise ImportError("Unsupported operating system")


def wait_robot(robot, ec):
    """等待机器人运动完成"""
    import time
    while True:
        state = robot.operationState(ec)
        if (state == xCoreSDK_python.OperationState.idle
                or state == xCoreSDK_python.OperationState.unknown):
            break
        time.sleep(0.1)


def minimal_move_example(robot, ec, target_position, speed):
    """最小移动示例"""
    print("开始最小移动示例")
    
    # 设置为自动模式并上电
    robot.setOperateMode(xCoreSDK_python.OperateMode.automatic, ec)
    print(f"设置操作模式: {ec}")
    
    robot.setPowerState(True, ec)
    print(f"设置上电状态: {ec}")
    
    # 设置默认速度和转弯区
    robot.setDefaultSpeed(100, ec)  # 100 mm/s
    robot.setDefaultZone(10, ec)    # 10mm转弯区
    
    # 定义目标点位 (X, Y, Z, Rx, Ry, Rz
    
    # 创建笛卡尔位置对象
    cart_pos = xCoreSDK_python.CartesianPosition(target_position)
    
    # 使用moveL进行直线运动
    print("使用moveL移动到目标点位")
    movelcmd = xCoreSDK_python.MoveJCommand(cart_pos, speed, 10)  # 速度100mm/s, 加速度10mm/s²
    cmdID = xCoreSDK_python.PyString()
    
    # 添加运动指令并开始执行
    robot.moveAppend([movelcmd], cmdID, ec)
    print(f"添加指令, Command ID: {cmdID.content()}, 结果: {ec}")
    
    robot.moveStart(ec)
    print(f"开始运动: {ec}")
    
    # 等待运动完成
    wait_robot(robot, ec)
    print("运动完成")


if __name__ == "__main__":
    try:
        # 连接机器人
        ip = "192.168.2.160"  # 需要根据实际IP地址修改
        robot = xCoreSDK_python.xMateRobot(ip)
        ec = {}
        
        # 连接机器人
        robot.connectToRobot(ec)
        print(f"连接机器人: {ec}")
        
        target_position = [-0.5221902637014976, -0.0491701709811159, 0.20, -0.7593015289499597, -0.15904156349466878, 1.3728508844992975]

        P2 =  [0.006166547587765699, -0.20601908072614283, 0.5707272660113739, 2.3489172405220207, -0.05228418876423481, -0.7842757862784905]

        P3 = [-0.1977019136436981, -0.39937271352807574, 0.4529230362491038, 2.3026080868759613, 0.10981666956657357, -0.8181736775572053]

        P3_2 = [-0.1977019136436981, -0.39937271352807574, 0.454, 2.3026080868759613, 0.10981666956657357, -0.8181736775572053]

        P4 = [-0.2262797643311764, -0.4174261607975159, 0.43380300226310675, 2.302071585446989, 0.05588512566021416, -0.8325993467318936]

        Pt = [-0.18919757, -0.38374264 , 0.45254227 , 2.34147996 , 0.21074746 ,-0.65914492]
    
        # 执行最小移动示例
        minimal_move_example(robot, ec, P2, 300)

        # minimal_move_example(robot, ec, P3, 300)

        # minimal_move_example(robot, ec, P3_2, 300)

        # minimal_move_example(robot, ec, Pt, 300)

        
        
        # 断开连接
        robot.disconnectFromRobot(ec)
        print(f"断开连接: {ec}")
        
    except Exception as e:
        print(f"发生错误: {e}")