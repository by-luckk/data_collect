#!/usr/bin/env python3
"""
从transformation_matrices.txt文件中提取Pt点和T矩阵数据
"""

import re


def extract_data_from_file(filename):
    """
    从文件中提取Pt点和T矩阵数据
    """
    with open(filename, 'r') as f:
        content = f.read()
    
    # 查找所有Pt点数据（以[开头，以]结尾的行）
    pt_pattern = r'\[([^\]]+)\]'
    pt_matches = re.findall(pt_pattern, content)
    
    pts = []
    for match in pt_matches:
        # 尝试将匹配的内容转换为数字列表
        try:
            # 分割字符串并转换为浮点数
            numbers = [float(x.strip()) for x in match.split(',')]
            # 只有当数字个数为6时才认为是有效的Pt点
            if len(numbers) == 6:
                pts.append(numbers)
        except ValueError:
            # 如果转换失败，跳过这个匹配
            continue
    
    # 查找所有4x4变换矩阵
    matrix_pattern = r'Transformation Matrix:\s*\n((?:\s*[-\d\.]+\s+[-\d\.]+\s+[-\d\.]+\s+[-\d\.]+\s*\n){4})'
    matrix_matches = re.findall(matrix_pattern, content)
    
    ts = []
    for match in matrix_matches:
        try:
            # 解析4x4矩阵
            matrix_lines = match.strip().split('\n')
            matrix = []
            for line in matrix_lines:
                row = [float(x.strip()) for x in line.split()]
                if len(row) == 4:  # 确保每行有4个数字
                    matrix.append(row)
            # 只有当矩阵是4x4时才认为是有效的
            if len(matrix) == 4:
                ts.append(matrix)
        except ValueError:
            # 如果转换失败，跳过这个匹配
            continue
    
    return pts, ts


def append_summary_to_file(filename, pts, ts):
    """
    将Pt点和T矩阵的汇总信息追加到文件末尾
    """
    with open(filename, 'a') as f:
        f.write("\n\n" + "="*60 + "\n")
        f.write("数据汇总\n")
        f.write("="*60 + "\n")
        
        f.write(f"\n总共找到 {len(pts)} 个Pt点:\n")
        for i, pt in enumerate(pts):
            f.write(f"Pt[{i:2d}]: [{', '.join(f'{x:9.6f}' for x in pt)}]\n")
        
        f.write(f"\n总共找到 {len(ts)} 个T矩阵:\n")
        for i, t in enumerate(ts):
            f.write(f"\nT[{i:2d}]:\n")
            for row in t:
                f.write("    " + " ".join(f"{val:10.6f}" for val in row) + "\n")


def main():
    """
    主函数
    """
    filename = "transformation_matrices.txt"
    
    try:
        pts, ts = extract_data_from_file(filename)
        
        print(f"成功提取 {len(pts)} 个Pt点和 {len(ts)} 个T矩阵")
        
        # 显示前几个结果
        print("\n前3个Pt点:")
        for i in range(min(3, len(pts))):
            print(f"Pt[{i:2d}]: [{', '.join(f'{x:9.6f}' for x in pts[i])}]")
        
        print("\n前2个T矩阵:")
        for i in range(min(2, len(ts))):
            print(f"\nT[{i:2d}]:")
            for j, row in enumerate(ts[i]):
                print("    " + " ".join(f"{val:10.6f}" for val in row))
        
        # 将汇总信息追加到文件
        append_summary_to_file(filename, pts, ts)
        print(f"\n汇总信息已追加到 {filename} 文件末尾")
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 {filename}")
    except Exception as e:
        print(f"处理文件时出错: {e}")


if __name__ == "__main__":
    main()