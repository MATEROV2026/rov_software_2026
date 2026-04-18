from shared.robot_interface import RobotInterface
from laptop.laptop_controller import LaptopController

class RosRobotInterface(RobotInterface):
    def __init__(self):
        self._controller = LaptopController()

    def run_task(self, task_id: str):
        return {"ok": True, "task_id": task_id, "message": "task received"}

    def run_reconstruction(self, task_id: str, image_paths: list[str]):
        self._controller.send_command("run_reconstruction")
        result = self._controller.wait_for_status("reconstruction_done", timeout=30.0)
        return result


    def get_status(self):
        return {"ok": True, "connected": True, "mode": "ros2"}
