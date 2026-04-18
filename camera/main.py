import pyzed.sl as sl
import numpy as np
import cv2

init = sl.InitParameters()
init.camera_resolution = sl.RESOLUTION.HD720
init.depth_mode = sl.DEPTH_MODE.ULTRA\
init.camera_fps = 60

print(zed.get_camera_information())
