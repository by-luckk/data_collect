'''力控示例'''
import math
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
from base_example import get_posture
from base_example import get_operationState

M_PI = math.pi
M_PI_2 = math.pi / 2

def fc_cartesian_control(robot,ec):
    '''笛卡尔控制力控。适用机型：xMateCR'''
    # 设置手持工具坐标系，Ry旋转90°
    toolset1 = xCoreSDK_python.Toolset()
    toolset1.end.rpy[1] = M_PI_2
    robot.setToolset(toolset1, ec)

    fc = robot.forceControl()
    # 力控初始化，使用世界
    # 坐标系
    fc.fcInit(xCoreSDK_python.FrameType.world, ec)
    print_log("fcInit",ec)
    # 笛卡尔控制模式

    fc.setControlType(1, ec)
    print_log("setControlType",ec)

     # 设置笛卡尔刚度。本示例用的是世界坐标系，所以世界坐标系的x方向0阻抗，其余方向阻抗较大
    fc.setCartesianStiffness([0, 100, 500, 500, 500, 500], ec)

    print_log("setCartesianStiffness",ec)
    # 开始力控
    print( "开始笛卡尔模式力控")
    fc.fcStart(ec)
    print_log("fcStart",ec)
    
    # 设置负载, 请根据实际情况设置，确保安全
    #   load = xCoreSDK_python.Load()
    #   load.mass = 1
    #   fc.setLoad(load, ec)
    # print_log("setLoad",ec)
    
    # 设置期望力
    fc.setCartesianDesiredForce([0, 0, 1, 0, 0, 0], ec)   #  依次为: X Y Z 方向笛卡尔期望力  X Y Z 方向笛卡尔期望力矩
    print_log("setCartesianDesiredForce",ec)

    # 按回车结束力控
    press_enter_for_finish()
    fc.fcStop(ec)
    print_log("fcStop",ec)
    
def fc_joint_control(fc,ec):
    '''关节模式力控。适用机型：xMateCR'''
    
    fc.fcInit(xCoreSDK_python.FrameType.base, ec)
    print_log("fcInit",ec)
    fc.setControlType(0, ec)
    print_log("setControlType",ec)
    # 设置各轴刚度。2轴4轴小阻抗，其余轴阻抗较大
    fc.setJointStiffness([1000, 10, 1000, 5, 50, 50], ec)
    print_log("setJointStiffness",ec)

    print("开始关节模式力控")
    fc.fcStart(ec)
    print_log("fcStart",ec)
    #  设置期望力
    fc.setJointDesiredTorque([1,1,3,0,0,0], ec)
    print_log("setJointDesiredTorque",ec)

    # 按回车结束力控
    press_enter_for_finish()
    fc.fcStop(ec)
    print_log("fcStop",ec)

def fc_overlay(robot,ec):
    '''搜索运动 & 力控监控。测试机型：xMateER3'''

    # 设置手持工具坐标系，Ry旋转90°
    # toolset1 = xCoreSDK_python.Toolset()
    # toolset1.end.rpy[1] = M_PI_2
    # robot.setToolset(toolset1, ec)
    # print_log("setToolset",ec)

    # """设置工具工件（仅平移，无旋转）"""
    # print_separator("set_toolset", length=80)
    #
    # # 创建工具工件对象
    # toolset = xCoreSDK_python.Toolset()
    #
    # # 设置工具工件的平移偏移（单位：米）
    # toolset.end.trans = [0.1, 0.05, 0.2]  # 例如，X 方向 10cm，Y 方向 5cm，Z 方向 20cm
    #
    # # 确保工具工件的旋转偏移为 [0, 0, 0]
    # toolset.end.rpy = [0, 0, 0]  # 没有 RPY 角度偏移
    #
    # # 设置工具工件到机器人
    # robot.setToolset(toolset, ec)
    #
    # print_log("setToolset", ec)
    # print(f"工具工件已设置：\n 平移: {toolset.end.trans} \n 旋转: {toolset.end.rpy}")



    fc = robot.forceControl()

    # # 可选：设置力控监控参数，示例里用的参数是xMateER3机型默认阈值
    #
    # # 设置最大轴速度
    #
    # fc.setJointMaxVel([3.0, 3.0, 3.5, 3.5, 3.5, 4.0], ec)
    # print_log("setJointMaxVel",ec)
    #
    # # 设置最大轴动量
    #
    # fc.setJointMaxMomentum([0.1, 0.1, 0.1, 0.055, 0.055, 0.055], ec)
    # print_log("setJointMaxMomentum",ec)
    #
    # # 设置最大轴动能
    #
    # fc.setJointMaxEnergy([250, 250, 250, 150, 150, 100], ec)
    # print_log("setJontMaxEnergy",ec)
    #
    # #设置笛卡尔空间最大速度
    #
    # fc.setCartesianMaxVel([50, 50, 50, 50, 50, 50], ec)
    # print_log("setCartesianMaxVel",ec)
    # #开始监控
    # fc.fcMonitor(True, ec)
    # print_log("fcMonitor",ec)

    #力控初始化
    fc.fcInit(xCoreSDK_python.FrameType.world, ec)
    # fc.fcInit(xCoreSDK_python.FrameType.tool, ec)
    print_log("fcInit",ec)
    
    #搜索运动必须为笛卡尔阻抗控制
    fc.setControlType(1, ec)
    fc.setCartesianStiffness([6000, 6000, 6000, 300, 300, 300], ec)
    print_log("setControlType",ec)


    # 设置期望力
    fc.setCartesianDesiredForce([30, 30, 50, 5, 5, 5], ec)   #  依次为: X Y Z 方向笛卡尔期望力  X Y Z 方向笛卡尔期望力矩
    print_log("setCartesianDesiredForce",ec)


    #设置绕Z轴(因为前面指定了力控坐标系为工具坐标系，所有这里是工具Z轴)的正弦搜索运动

    fc.setSineOverlay(2, 5, 5, M_PI, 1, ec)
    # fc.setSineOverlay(2, 20, 1, 0, 0, ec)
    print_log("setSineOverlay",ec)
    #开始力控
    fc.fcStart(ec)
    print_log("fcStart",ec)

    #叠加XZ平面莉萨如搜索运动
    fc.setLissajousOverlay(2, 5, 5, 5, 5, 0, ec)
    # fc.setLissajousOverlay(1, 0, 0, 0, 0, 0, ec)
    print_log("setLissajousOverlay",ec)

    print_separator("get_posture", length=80)
    pos = robot.posture(xCoreSDK_python.CoordinateType.endInRef, ec)
    print_log("posture", ec, ', '.join(map(str, pos)))
    # 打印修改后的 pos
    pos[2] = 0.7

    print("修改后的 pos:", pos)

    '''moveL运动'''
    print_separator("moveL", length=80)
    movelcmd = xCoreSDK_python.MoveLCommand(pos, 1000, 10)
    cmdID = xCoreSDK_python.PyString()
    robot.moveAppend([movelcmd], cmdID, ec)  # [movelcmd]指令列表，可以添加多条指令，须为同类型指令
    print("Command ID:", cmdID.content())
    print_log("moveAppend", ec)
    robot.moveStart(ec)
    print_log("moveStart", ec)
    get_operationState(robot, ec)
    wait_robot(robot, ec)
    get_operationState(robot, ec)

    pos[2] = 0.30
    print_separator("moveL", length=80)
    movelcmd = xCoreSDK_python.MoveLCommand(pos, 500, 10)
    cmdID = xCoreSDK_python.PyString()
    robot.moveAppend([movelcmd], cmdID, ec)  # [movelcmd]指令列表，可以添加多条指令，须为同类型指令
    print("Command ID:", cmdID.content())
    print_log("moveAppend", ec)
    robot.moveStart(ec)
    print_log("moveStart", ec)
    get_operationState(robot, ec)
    wait_robot(robot, ec)
    get_operationState(robot, ec)




    #开始搜索运动
    print("开始搜索运动")
    fc.startOverlay(ec)
    print_log("startOverlay",ec)
    fc.setCartesianStiffness([100, 100, 800, 30, 30, 30], ec)


    # #获得位置
    # print_separator("get_posture", length=80)
    # pos = robot.posture(xCoreSDK_python.CoordinateType.endInRef, ec)
    # print_log("posture", ec, ', '.join(map(str, pos)))
    # # 打印修改后的 pos
    # pos[2]= 0.7
    #
    # print("修改后的 pos:", pos)
    #
    # '''moveL运动'''
    # print_separator("moveL", length=80)
    # movelcmd = xCoreSDK_python.MoveJCommand(pos, 1000, 10)
    # cmdID = xCoreSDK_python.PyString()
    # robot.moveAppend([movelcmd], cmdID, ec)  # [movelcmd]指令列表，可以添加多条指令，须为同类型指令
    # print("Command ID:", cmdID.content())
    # print_log("moveAppend", ec)
    # robot.moveStart(ec)
    # print_log("moveStart", ec)
    # get_operationState(robot, ec)
    # wait_robot(robot, ec)
    # get_operationState(robot, ec)
    #
    # pos[2]=0.35
    # print_separator("moveL", length=80)
    # movelcmd = xCoreSDK_python.MoveJCommand(pos, 500, 10)
    # cmdID = xCoreSDK_python.PyString()
    # robot.moveAppend([movelcmd], cmdID, ec)  # [movelcmd]指令列表，可以添加多条指令，须为同类型指令
    # print("Command ID:", cmdID.content())
    # print_log("moveAppend", ec)
    # robot.moveStart(ec)
    # print_log("moveStart", ec)
    # get_operationState(robot, ec)
    # wait_robot(robot, ec)
    # get_operationState(robot, ec)

    pos[2]=0.17
    print_separator("moveL", length=80)
    movelcmd = xCoreSDK_python.MoveLCommand(pos, 80, 7)
    cmdID = xCoreSDK_python.PyString()
    robot.moveAppend([movelcmd], cmdID, ec)  # [movelcmd]指令列表，可以添加多条指令，须为同类型指令
    print("Command ID:", cmdID.content())
    print_log("moveAppend", ec)
    robot.moveStart(ec)
    print_log("moveStart", ec)
    get_operationState(robot, ec)
    wait_robot(robot, ec)
    get_operationState(robot, ec)
    #
    # print_separator("moveL", length=80)
    # movelcmd = xCoreSDK_python.MoveJCommand(pos, 500, 10)
    # cmdID = xCoreSDK_python.PyString()
    # robot.moveAppend([movelcmd], cmdID, ec)  # [movelcmd]指令列表，可以添加多条指令，须为同类型指令
    # print("Command ID:", cmdID.content())
    # print_log("moveAppend", ec)
    # robot.moveStart(ec)
    # print_log("moveStart", ec)
    # wait_robot(robot, ec)





    #暂停和重新开始搜索运动
    # fc.pauseOverlay(ec)
    # fc.restartOverlay(ec)


    #按回车结束力控
    press_enter_for_finish()
    fc.stopOverlay(ec)
    print_log("stopOverlay",ec)

    #监控参数恢复到默认值
    fc.fcMonitor(False, ec)
    print_log("fcMonitor",ec)
    #停止力控
    fc.fcStop(ec)
    print_log("fcStop",ec)

def fc_condition(robot,ec):
    '''设置力控终止条件。测试机型：xMateER3'''
    fc = robot.forceControl()
    toolset = xCoreSDK_python.Toolset()
    toolset.ref.trans[2] = 0.1
    robot.setToolset(toolset, ec)
    print_log("setToolset",ec)

    fc.fcInit(xCoreSDK_python.FrameType.world, ec)
    print_log("fcInit",ec)
    fc.setControlType(1, ec)
    print_log("setControlType",ec)
    fc.fcStart(ec)
    print_log("fcStart",ec)
    # 设置力限制
    fc.setForceCondition([-20, 20, -15, 15, -15, 15], True, 20, ec)
    print_log("setForceCondition",ec)
    # 设置长方体区域限制, isInside=false代表在这个区域内时终止等待
    # 长方体所在的坐标系，会叠加外部工件坐标系
    supvFrame = xCoreSDK_python.Frame()
    supvFrame.trans[2] = -0.1
    fc.setPoseBoxCondition(supvFrame, [-0.6, 0.6, -0.6, 0.6, 0.2, 0.3], False, 20, ec)
    print_log("setPoseBoxCondition",ec)

    # 阻塞等待满足终止条件
    print("开始等待")
    fc.waitCondition(ec)
    print_log("waitCondition",ec)

    print("等待结束，停止力控")
    fc.fcStop(ec)
    print_log("fcStop",ec)

def calibrate_force_sensor(robot,ec):
    '''力矩传感器标定'''
    # 标定全部轴
    robot.calibrateForceSensor(True, 0, ec)
    print_log("calibrateForceSensor",ec)
    # 单轴(4轴)标定
    robot.calibrateForceSensor(False, 3, ec)
    print_log("calibrateForceSensor",ec)

def read_torque_info(fc,ec):
    '''读取末端力矩信息'''
    joint_torque = xCoreSDK_python.PyTypeVectorDouble()
    external_torque = xCoreSDK_python.PyTypeVectorDouble()
    cart_force = xCoreSDK_python.PyTypeVectorDouble() 
    cart_torque = xCoreSDK_python.PyTypeVectorDouble()

    #   读取当前力矩信息
    fc.getEndTorque(xCoreSDK_python.FrameType.flange, joint_torque, external_torque, cart_torque, cart_force, ec)
    print("末端力矩")
    print("各轴测量力 -", joint_torque.content())
    print("各轴外部力 -", external_torque.content())
    print("笛卡尔力矩 -", cart_torque.content())
    print("笛卡尔力   -", cart_force.content())

def press_enter_for_finish():
    '''按回车结束力控'''
    while True:
        user_input = input("按回车结束力控：")
        if user_input == "":
            break
        else:
            print(f"没到位置")

def wait_for_finish():
    '''按回车结束力控'''
    while True:
        user_input = input("位置到按回车结束力控：")
        if user_input == "":
            break
        else:
            print(f"You entered: {user_input}")

def main():
    try:
        ip = "192.168.2.160"
        robot = xCoreSDK_python.xMateRobot(ip) 
        ec = {}
        # 力控类
        fc = robot.forceControl()
        read_torque_info(fc,ec)
        
        # 上电
        robot.setOperateMode(xCoreSDK_python.OperateMode.automatic, ec)
        robot.setPowerState(True, ec)
        
        # 先运动到拖拽位姿, 注意选择正确的机型
        drag_cr = [0, M_PI/6, -M_PI_2, 0, -M_PI/3, 0] # cr
        drag_er = [0, M_PI/6, M_PI/3, 0, M_PI_2, 0] # er
        abs_j = xCoreSDK_python.MoveAbsJCommand(drag_cr,1000)
        robot.executeCommand([abs_j], ec)

        wait_robot(robot, ec)



        # fc = robot.forceControl()
        # # 力控初始化，使用世界
        # # 坐标系
        # fc.fcInit(xCoreSDK_python.FrameType.world, ec)
        # print_log("fcInit", ec)
        # # 笛卡尔控制模式
        #
        # fc.setControlType(1, ec)
        # print_log("setControlType", ec)
        #
        # # 设置笛卡尔刚度。本示例用的是世界坐标系，所以世界坐标系的x方向0阻抗，其余方向阻抗较大
        # fc.setCartesianStiffness([0, 0, 0, 0, 0, 0], ec)
        #
        # print_log("setCartesianStiffness", ec)
        # # 开始力控
        # print("开始笛卡尔模式力控")
        # fc.fcStart(ec)
        # print_log("fcStart", ec)
        #
        # # 设置负载, 请根据实际情况设置，确保安全
        # #   load = xCoreSDK_python.Load()
        # #   load.mass = 1
        # #   fc.setLoad(load, ec)
        # # print_log("setLoad",ec)
        #
        # # 设置期望力
        # fc.setCartesianDesiredForce([0, 0, 1, 0, 0, 0], ec)  # 依次为: X Y Z 方向笛卡尔期望力  X Y Z 方向笛卡尔期望力矩
        # print_log("setCartesianDesiredForce", ec)


        # print_separator("moveL", length=80)
        # cart_pos = xCoreSDK_python.CartesianPosition(
        #     [-37.638*0.001, 697.956*0.001, 283.02*0.001, 3.14, 0, 3.14])  # s4点位
        # movelcmd = xCoreSDK_python.MoveLCommand(cart_pos, 1000, 10)
        # cmdID = xCoreSDK_python.PyString()
        # robot.moveAppend([movelcmd], cmdID, ec)                                                                                                                                   # [movelcmd]指令列表，可以添加多条指令，须为同类型指令
        # print("Command ID:", cmdID.content())
        # print_log("moveAppend", ec)
        # # robot.moveStart(ec)
        # print_log("moveStart", ec)
        # wait_robot(robot, ec)
        #
        # print_separator("moveL", length=80)
        # # cart_pos = xCoreSDK_python.CartesianPosition(
        # #     [-37.638 * 0.001, 697.956 * 0.001, 242.02 * 0.001, 3.14, 0, 3.14])  # s4点位
        #
        # cart_pos = xCoreSDK_python.CartesianPosition(
        #     [-37.638 * 0.001, 697.956 * 0.001, 600.02 * 0.001, 3.14, 0, 3.14])  # s4点位
        #
        # movelcmd = xCoreSDK_python.MoveLCommand(cart_pos, 100, 10)
        # cmdID = xCoreSDK_python.PyString()
        # robot.moveAppend([movelcmd], cmdID, ec)  # [movelcmd]指令列表，可以添加多条指令，须为同类型指令
        # print("Command ID:", cmdID.content())
        # print_log("moveAppend", ec)
        # robot.moveStart(ec)
        # print_log("moveStart", ec)
        # wait_robot(robot, ec)
        # # 按回车结束力控
        # press_enter_for_finish()
        # fc.fcStop(ec)
        # print_log("fcStop", ec)
        # 获得位置







        # 运行示例程序
        # calibrate_force_sensor(robot,ec)
        # fc_cartesian_control(robot,ec)
        # fc_joint_control(fc,ec)
        # fc_condition(robot,ec)
        fc_overlay(robot, ec)
        
        robot.setPowerState(False, ec)
        robot.setOperateMode(xCoreSDK_python.OperateMode.manual, ec)
    except Exception as e:
        print(f"An error occurred: {e}")
if __name__ == '__main__':
    main()