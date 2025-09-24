'''力控示例引入头文件'''
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
from log import print_log
from move_example import wait_robot

M_PI = math.pi
M_PI_2 = math.pi / 2