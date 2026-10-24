import sys

import pyzed.sl as sl


def main() -> int:
    init = sl.InitParameters()
    init.camera_resolution = sl.RESOLUTION.HD720
    init.depth_mode = sl.DEPTH_MODE.ULTRA          # or NEURAL
    init.camera_fps = 60
    init.coordinate_units = sl.UNIT.METER
    init.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP

    zed = sl.Camera()
    status = zed.open(init)
    if status != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to open ZED camera: {status}")
        return 1

    try:
        info = zed.get_camera_information()
        print(info)

        # Positional tracking must be enabled before spatial mapping
        status = zed.enable_positional_tracking(sl.PositionalTrackingParameters())
        if status != sl.ERROR_CODE.SUCCESS:
            print(f"Failed to enable positional tracking: {status}")
            return 1

        mapping = sl.SpatialMappingParameters()
        mapping.map_type = sl.SPATIAL_MAP_TYPE.MESH   # or FUSED_POINT_CLOUD
        mapping.resolution_meter = 0.05               # smaller = more detail, more memory
        mapping.range_meter = 5.0                     # max depth used for mapping
        mapping.save_texture = True                   # needed for mesh.apply_texture()
        status = zed.enable_spatial_mapping(mapping)
        if status != sl.ERROR_CODE.SUCCESS:
            print(f"Failed to enable spatial mapping: {status}")
            return 1

        # Capture loop: mapping updates in the background on every grab()
        print("Scanning... move the camera slowly.")
        mesh = sl.Mesh()
        for _ in range(2000):
            if zed.grab() == sl.ERROR_CODE.SUCCESS:
                pass

        # Extract, clean up, texture and save
        print("Extracting map...")
        zed.extract_whole_spatial_map(mesh)
        mesh.filter(sl.MeshFilterParameters())
        mesh.apply_texture(sl.MESH_TEXTURE_FORMAT.RGB)
        mesh.save("map.obj")
        print("Saved map.obj")

        zed.disable_spatial_mapping()
        zed.disable_positional_tracking()
    finally:
        zed.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
