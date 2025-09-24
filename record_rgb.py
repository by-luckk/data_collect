
import os
import time
import json
import cv2
import numpy as np
import pyrealsense2 as rs

class SynchronizedRecorder:
    def __init__(self, save_dir="recorded_data", interval=0.05):
        self.save_dir = save_dir
        self.images_dir = os.path.join(save_dir, "images")
        os.makedirs(self.images_dir, exist_ok=True)
        self.data = []  # 保存所有同步记录
        self.interval = interval

        # 初始化 RealSense
        self.pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        self.pipeline.start(config)

    def record(self, record_time=10):
        print(f"Start synchronized recording for {record_time} seconds...")
        start_time = time.time()

        try:
            while time.time() - start_time < record_time:
                timestamp = time.time()

                # 捕获一张 RGB 图像
                frames = self.pipeline.wait_for_frames()
                color_frame = frames.get_color_frame()
                if color_frame is None:
                    print("No color frame captured, skip one frame.")
                    continue

                img = np.asanyarray(color_frame.get_data())

                # 保存图像
                img_filename = f"{timestamp:.6f}.png"
                img_path = os.path.join(self.images_dir, img_filename)
                cv2.imwrite(img_path, img)

                # 实时显示图像
                cv2.imshow('RealSense RGB Live', img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("Manual stop detected.")
                    break

                # 记录一条数据（这里只记录时间戳和图像文件名）
                record = {
                    "timestamp": timestamp,
                    "image_filename": img_filename
                }
                self.data.append(record)

                print(f"Recorded frame at {timestamp:.6f}")
                time.sleep(self.interval)
        finally:
            self.pipeline.stop()

            # 保存整体数据
            with open(os.path.join(self.save_dir, "image_data.json"), "w") as f:
                json.dump(self.data, f, indent=4)
            print(f"Data saved to {self.save_dir}")

if __name__ == "__main__":
    recorder = SynchronizedRecorder(
        save_dir="recorded_data_5082",
        interval=0.4  # 20Hz
    )
    while True:
        recorder.record(record_time=200)
