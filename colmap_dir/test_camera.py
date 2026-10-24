import pyzed.sl as sl
import cv2
import os
import time

# Create output folder
output_dir = "images"
os.makedirs(output_dir, exist_ok=True)

# Init camera
zed = sl.Camera()

init_params = sl.InitParameters()
init_params.depth_mode = sl.DEPTH_MODE.NONE   # 🔑 disable depth (fix your error)
init_params.camera_resolution = sl.RESOLUTION.HD720

# Open camera
if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
    print("Failed to open camera")
    exit()

print("Camera opened")

image = sl.Mat()
i = 0
max_images = 100   # change as needed

print("Starting capture... move the camera slowly!")

while i < max_images:
    if zed.grab() == sl.ERROR_CODE.SUCCESS:
        zed.retrieve_image(image, sl.VIEW.LEFT)
        frame = image.get_data()

        filename = os.path.join(output_dir, f"img_{i:03d}.jpg")
        cv2.imwrite(filename, frame)

        print(f"Saved {filename}")
        i += 1

        time.sleep(0.5)  # 🔑 move camera between shots

zed.close()
print("Done capturing!")