## License: Apache 2.0. See LICENSE file in root directory.
## Copyright(c) 2017 Intel Corporation. All Rights Reserved.

#####################################################
##              Align Depth to Color               ##
#####################################################

# First import the library
import pyrealsense2 as rs
# Import Numpy for easy array manipulation
import numpy as np
# Import OpenCV for easy image rendering
import cv2
import os

root_dir = "debug/funny"
topic = "fans"
mode = "save"
# rgb_dir = "debug/hand/Disinfectant/rgb"
rgb_dir = os.path.join(root_dir, topic, "rgb")
depth_dir = os.path.join(root_dir, topic, "depth")

os.makedirs(rgb_dir, exist_ok=True)
os.makedirs(depth_dir, exist_ok=True)

# Create a pipeline
pipeline = rs.pipeline()

# Create a config and configure the pipeline to stream
#  different resolutions of color and depth streams
config = rs.config()

# Get device product line for setting a supporting resolution
pipeline_wrapper = rs.pipeline_wrapper(pipeline)
pipeline_profile = config.resolve(pipeline_wrapper)
device = pipeline_profile.get_device()
device_product_line = str(device.get_info(rs.camera_info.product_line))

found_rgb = False
for s in device.sensors:
    if s.get_info(rs.camera_info.name) == 'RGB Camera':
        found_rgb = True
        break
if not found_rgb:
    print("The demo requires Depth camera with Color sensor")
    exit(0)

config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# Start streaming
profile = pipeline.start(config)

profile_color = profile.get_stream(rs.stream.color)
intr_color = profile_color.as_video_stream_profile().get_intrinsics()
print(f"color : {intr_color}") 

# Getting the depth sensor's depth scale (see rs-align example for explanation)
depth_sensor = profile.get_device().first_depth_sensor()
depth_scale = depth_sensor.get_depth_scale()
print("Depth Scale is: " , depth_scale)

# We will be removing the background of objects more than
#  clipping_distance_in_meters meters away
clipping_distance_in_meters = 1 #1 meter
clipping_distance = clipping_distance_in_meters / depth_scale

# Create an align object
# rs.align allows us to perform alignment of depth frames to others frames
# The "align_to" is the stream type to which we plan to align depth frames.
align_to = rs.stream.color
align = rs.align(align_to)
save_count= 0
save_flag = 0
frame_count = 0

# Streaming loop
try:
    while True:
        # Get frameset of color and depth
        frames = pipeline.wait_for_frames()
        # frames.get_depth_frame() is a 640x360 depth image

        # Align the depth frame to color frame
        aligned_frames = align.process(frames)

        # Get aligned frames
        aligned_depth_frame = aligned_frames.get_depth_frame() # aligned_depth_frame is a 640x480 depth image
        color_frame = aligned_frames.get_color_frame()

        # Validate that both frames are valid
        if not aligned_depth_frame or not color_frame:
            continue

        depth_image = np.asanyarray(aligned_depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        if frame_count > 30 and frame_count % 1 == 0:
            # 保存RGB图像
            if save_flag == 0 and mode=="save":
                # input("Press Enter to continue...")
                save_flag = 1
            save_count = save_count + 1
            rgb_filename = os.path.join(rgb_dir, f"{save_count:06d}.png")
            
            # 保存深度图像（颜色映射后的）
            depth_filename = os.path.join(depth_dir, f"{save_count:06d}.png")
            if mode=="save":
                cv2.imwrite(rgb_filename, color_image)
                cv2.imwrite(depth_filename, depth_image)

            # 打印保存的文件名
            print(f"Saved: {rgb_filename}, {depth_filename}")

        # 将深度图像转换为彩色映射（便于可视化）
        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET
        )

        combined_image = cv2.hconcat([color_image, depth_colormap])
        
        cv2.imshow('RGB and Depth', combined_image)
        frame_count += 1

        # 按下 'q' 键退出
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    pipeline.stop()