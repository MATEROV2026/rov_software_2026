import sys

import pyzed.sl as sl


def main() -> int:
    init = sl.InitParameters()
    init.camera_resolution = sl.RESOLUTION.HD720
    init.depth_mode = sl.DEPTH_MODE.ULTRA
    init.camera_fps = 60

    zed = sl.Camera()
    status = zed.open(init)
    if status != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to open ZED camera: {status}")
        return 1

    try:
        info = zed.get_camera_information()
        print(info)
    finally:
        zed.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
