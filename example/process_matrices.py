#!/usr/bin/env python3
"""
处理transformation_matrices.txt文件中的数据，提取Pt和T矩阵列表
"""

import numpy as np
import re


def parse_transformation_file(filename):
    """
    解析transformation_matrices.txt文件，提取Pt和T矩阵列表
    """
    with open(filename, 'r') as f:
        content = f.read()
    
    # 分割每组数据
    # 每组数据以"Timestamp:"开头
    groups = re.split(r'(Timestamp:\s*\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2}:\d{2})', content)
    
    # 移除空字符串并重新组织数据
    groups = [g.strip() for g in groups if g.strip()]
    
    pts = []  # 存储Pt点列表
    ts = []   # 存储T矩阵列表
    
    i = 0
    while i < len(groups):
        # 查找包含Pt的数据行
        if groups[i].startswith('Timestamp:'):
            # 查找Pt数据（在Transformation Matrix之前）
            matrix_index = i + 1
            if matrix_index < len(groups):
                # Pt数据在Transformation Matrix之前
                lines = groups[matrix_index].split('\n')
                pt_line = None
                matrix_lines = []
                
                for line in lines:
                    if line.startswith('[') and line.endswith(']'):
                        pt_line = line
                    elif line.startswith(('0.', '1.', '-0.', '-1.')) or 'Transformation Matrix:' in line:
                        if 'Transformation Matrix:' not in line:
                            matrix_lines.append(line)
                
                # 解析Pt点
                if pt_line:
                    pt_str = pt_line.strip('[]')
                    pt = [float(x.strip()) for x in pt_str.split(',')]
                    pts.append(pt)
                
                # 解析T矩阵（4x4）
                if len(matrix_lines) >= 4:
                    matrix = []
                    for j in range(4):
                        row = [float(x) for x in matrix_lines[j].split()]
                        matrix.append(row)
                    ts.append(matrix)
        i += 1
    
    return pts, ts


def append_results_to_file(filename, pts, ts):
    """
    将结果追加到文件末尾
    """
    with open(filename, 'a') as f:
        f.write("\n\n" + "="*50 + "\n")
        f.write("整理结果\n")
        f.write("="*50 + "\n")
        
        f.write(f"\nPt点列表 (共{len(pts)}个):\n")
        for i, pt in enumerate(pts):
            f.write(f"Pt[{i}]: {pt}\n")
        
        f.write(f"\nT矩阵列表 (共{len(ts)}个):\n")
        for i, t in enumerate(ts):
            f.write(f"T[{i}]:\n")
            for row in t:
                f.write(" ".join(f"{val:10.6f}" for val in row) + "\n")
            f.write("\n")


def main():
    """
    主函数
    """
    filename = "transformation_matrices.txt"
    
    try:
        pts, ts = parse_transformation_file(filename)
        print(f"成功解析 {len(pts)} 个Pt点和 {len(ts)} 个T矩阵")
        
        # 打印前几个结果进行验证
        print("\n前3个Pt点:")
        for i in range(min(3, len(pts))):
            print(f"Pt[{i}]: {pts[i]}")
        
        print("\n前3个T矩阵:")
        for i in range(min(3, len(ts))):
            print(f"T[{i}]:")
            for row in ts[i]:
                print(" ".join(f"{val:10.6f}" for val in row))
        
        # 将结果追加到文件
        append_results_to_file(filename, pts, ts)
        print(f"\n结果已追加到 {filename} 文件末尾")
        
    except Exception as e:
        print(f"处理文件时出错: {e}")


if __name__ == "__main__":
    main()