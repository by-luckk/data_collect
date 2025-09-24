import pyrealsense2 as rs

# 目标内参配置
TARGET_INTRINSICS = {
    'fx': 387.08,
    'fy': 387.08,
    'cx': 322.95,
    'cy': 238.42,
    'width': 640,
    'height': 480
}

def override_intrinsics():
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, TARGET_INTRINSICS['width'], TARGET_INTRINSICS['height'], rs.format.z16, 30)
    config.enable_stream(rs.stream.color, TARGET_INTRINSICS['width'], TARGET_INTRINSICS['height'], rs.format.bgr8, 30)
    profile = pipeline.start(config)

    # 获取原始内参
    depth_intr = profile.get_stream(rs.stream.depth).as_video_stream_profile().get_intrinsics()
    color_intr = profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()

    print("[原始内参]")
    print(f"Depth: fx={depth_intr.fx:.2f}, fy={depth_intr.fy:.2f}, cx={depth_intr.ppx:.2f}, cy={depth_intr.ppy:.2f}")
    print(f"Color: fx={color_intr.fx:.2f}, fy={color_intr.fy:.2f}, cx={color_intr.ppx:.2f}, cy={color_intr.ppy:.2f}")

    # 修改内参（软件层覆盖）
    for intr in [depth_intr, color_intr]:
        intr.fx = TARGET_INTRINSICS['fx']
        intr.fy = TARGET_INTRINSICS['fy']
        intr.ppx = TARGET_INTRINSICS['cx']
        intr.ppy = TARGET_INTRINSICS['cy']
        intr.width = TARGET_INTRINSICS['width']
        intr.height = TARGET_INTRINSICS['height']

    print("\n[修改后内参]")
    print(f"Depth: fx={depth_intr.fx:.2f}, fy={depth_intr.fy:.2f}, cx={depth_intr.ppx:.2f}, cy={depth_intr.ppy:.2f}")
    print(f"Color: fx={color_intr.fx:.2f}, fy={color_intr.fy:.2f}, cx={color_intr.ppx:.2f}, cy={color_intr.ppy:.2f}")

    pipeline.stop()
    return depth_intr, color_intr

if __name__ == '__main__':
    override_intrinsics()
    