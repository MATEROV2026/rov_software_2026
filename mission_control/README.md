# Mission control desktop (Matrov)

FastAPI backend + CustomTkinter GUI for ROV task selection, instructions, image
uploads, and robot commands (mock interface today; swap for ROS2/Jetson later).

## Setup

```bash
cd mission_control
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
```

## Run

Terminal 1 — API:

```bash
cd mission_control
source .venv/bin/activate
python run_backend.py
```

Terminal 2 — GUI:

```bash
cd mission_control
source .venv/bin/activate
python gui/app.py
```

API default: `http://127.0.0.1:8000`. Optional pygame joystick: see
`requirements-joystick.txt` (Linux/Windows only).

## Layout

| Path | Role |
|------|------|
| `backend/` | FastAPI app, `tasks.json`, upload storage |
| `gui/` | CustomTkinter screens and API client |
| `shared/` | `RobotInterface` + mock implementation |

## macOS notes

If `tkinter.Tk()` aborts, use Homebrew Python 3.12 and a fresh venv. Run
`python diagnose_gui.py` from this folder to verify Tcl/Tk.
