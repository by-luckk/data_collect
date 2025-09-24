
import os
import numpy as np
import json
import matplotlib.pyplot as plt
import cv2

def visualize_raw_pressure(json_path="xhand_pressure_data.json", finger_index=0):
    """静态可视化函数 - 从JSON文件读取数据并保存图像"""
    with open(json_path, "r") as f:
        data = json.load(f)

    raw_pressure = data[finger_index]["raw_pressure"]  # shape: (120, 3)
    fx_values = np.array([p[2] for p in raw_pressure])  # 只取 fx 分量

    if len(fx_values) != 120:
        raise ValueError("raw_pressure 不为 120 个点")

    # reshape 成 10x12（按列主顺序）
    fx_grid = fx_values.reshape((10, 12))

    plt.figure(figsize=(8, 6))
    plt.imshow(fx_grid, cmap='viridis', origin='lower')
    plt.colorbar(label='fx pressure')
    plt.title(f'Finger {finger_index} Raw Pressure (fx)')
    plt.xlabel("Column")
    plt.ylabel("Row")
    plt.savefig(f"results/xhand_pressure_data_finger_{finger_index}.png")

def create_pressure_visualization(pressure_data, window_size=(800, 600)):
    """
    实时创建五个手指的压力可视化图像
    x分量用颜色深浅表示，yz分量用箭头表示
    
    Args:
        pressure_data: 压力传感器数据列表，每个元素包含5个手指的数据
        window_size: 窗口大小 (width, height)
    
    Returns:
        cv2图像数组，用于显示
    """
    if len(pressure_data) < 5:
        print(f"Warning: Expected 5 fingers, got {len(pressure_data)}")
        return None
    
    # 创建空白画布
    canvas = np.zeros((window_size[1], window_size[0], 3), dtype=np.uint8)
    
    # 每个手指的显示区域大小
    finger_width = window_size[0] // 5
    finger_height = window_size[1]
    
    # 固定最大值
    x_max = 20.0
    yz_max = 5.0
    
    for finger_idx in range(5):
        if finger_idx >= len(pressure_data):
            continue
            
        sensor_data = pressure_data[finger_idx]
        raw_pressure = sensor_data.get("raw_pressure", [])
        
        if len(raw_pressure) != 120:
            continue
            
        # 提取xyz分量
        fx_values = np.array([p[0] for p in raw_pressure])  # fx分量
        fy_values = np.array([p[1] for p in raw_pressure])  # fy分量
        fz_values = np.array([p[2] for p in raw_pressure])  # fz分量
        
        # reshape为10x12
        fx_grid = fx_values.reshape((10, 12))
        fy_grid = fy_values.reshape((10, 12))
        fz_grid = fz_values.reshape((10, 12))
        
        # 计算显示位置
        x_start = finger_idx * finger_width
        x_end = (finger_idx + 1) * finger_width
        
        # 创建手指区域画布
        finger_canvas = np.zeros((finger_height, finger_width, 3), dtype=np.uint8)
        
        # 1. 用x分量设置背景颜色深浅
        fx_clipped = np.clip(fx_grid, 0, x_max)
        fx_normalized = (fx_clipped / x_max * 255).astype(np.uint8)
        fx_colored = cv2.applyColorMap(fx_normalized, cv2.COLORMAP_VIRIDIS)
        
        # 调整颜色图像大小并作为背景
        fx_resized = cv2.resize(fx_colored, (finger_width, finger_height))
        finger_canvas = fx_resized.copy()
        
        # 2. 绘制yz分量的箭头
        # 计算每个网格点的位置
        grid_height = finger_height // 10
        grid_width = finger_width // 12
        
        for row in range(10):
            for col in range(12):
                # 计算箭头中心位置
                center_x = col * grid_width + grid_width // 2
                center_y = row * grid_height + grid_height // 2
                
                # 获取该点的yz分量
                fy_val = fy_grid[row, col]
                fz_val = fz_grid[row, col]
                
                # 只有当yz分量不为0时才画箭头
                if abs(fy_val) > 0.01 or abs(fz_val) > 0.01:
                    # 归一化yz分量到箭头长度
                    fy_norm = fy_val / yz_max
                    fz_norm = fz_val / yz_max
                    
                    # 计算箭头终点（注意y轴方向相反）
                    end_x = center_x + int(fy_norm * grid_width * 0.4)
                    end_y = center_y - int(fz_norm * grid_height * 0.4)  # y轴翻转
                    
                    # 限制箭头在网格内
                    end_x = max(0, min(finger_width-1, end_x))
                    end_y = max(0, min(finger_height-1, end_y))
                    
                    # 计算箭头长度
                    arrow_length = np.sqrt((end_x - center_x)**2 + (end_y - center_y)**2)
                    
                    # 只有当箭头长度足够大时才绘制
                    if arrow_length > 2:
                        # 绘制箭头（白色，粗细根据长度调整）
                        thickness = max(1, min(3, int(arrow_length / 5)))
                        cv2.arrowedLine(finger_canvas, 
                                      (center_x, center_y), 
                                      (end_x, end_y), 
                                      (255, 255, 255),  # 白色箭头
                                      thickness, 
                                      tipLength=0.3)
        
        # 将手指画布放置到主画布上
        canvas[:, x_start:x_end] = finger_canvas
        
        # 添加手指标签
        cv2.putText(canvas, f"F{finger_idx}", 
                   (x_start + 5, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 添加压力值信息
        calc_pressure = sensor_data.get("calc_pressure", [0, 0, 0])
        pressure_text = f"X:{calc_pressure[0]:.1f} Y:{calc_pressure[1]:.1f} Z:{calc_pressure[2]:.1f}"
        cv2.putText(canvas, pressure_text, 
                   (x_start + 5, finger_height - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
    
    return canvas
