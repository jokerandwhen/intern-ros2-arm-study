# SoArm101 Dual-Arm Teleoperation & Vision-Based Grasping System

> Internship project (July–August 2026). Built a complete pipeline around the SoArm101 6-DOF robot arm: **direct single-arm control → leader-follower teleoperation → demonstration data collection → vision-based autonomous grasping → remote VLA inference verification**.
>
> [中文版](README.md)

## Overview

Using a SoArm101 leader-follower hardware setup (12 STS3215 serial bus servos in total), this project progressively implements:

1. **Low-level serial control** — pyserial implementation of the Feetech STS3215 half-duplex protocol, reading/writing servo registers for joint-level control;
2. **Leader-follower teleoperation** — the leader arm is moved by hand while the follower arm tracks it in real time for demonstration data collection;
3. **Demonstration recording & playback** — motions are recorded at 20 Hz, with both frame-by-frame and smoothed playback modes;
4. **Vision-based autonomous grasping** — using the follower arm's gripper camera, with both OpenCV HSV color detection and YOLOv8 object detection, including pixel-to-joint camera calibration and visual-servo fine alignment;
5. **Remote VLA inference verification** — WebSocket + msgpack communication with a remote VLA server, streaming camera images and receiving action commands.

## Hardware Setup

| Device | Details |
|--------|---------|
| Leader arm (teaching arm) | COM4, 12 V power, 12 V servos, moved by hand |
| Follower arm | COM3, 5 V power, 7.4 V servos, executes motions |
| Follower arm camera | USB camera, OpenCV index 2 (mounted on the gripper, looking down at the table) |
| Serial chip | CH343 USB-to-serial, baud rate 1,000,000 |
| Host PC | Windows 11, Python 3.10, CUDA GPU (YOLO inference acceleration) |

> **Wiring note**: The 2-pin jumper on the servo driver board must be shorted (common ground between USB and external power); otherwise communication becomes unstable.
>
> **Naming note**: Some early scripts (e.g. `main/sync_and_teleop.py`) refer to COM3 as "master" and COM4 as "puppet/auxiliary", which is the opposite of this document's role naming. This document uses hardware roles: **COM4 = leader arm (hand-moved), COM3 = follower arm (tracks and executes, carries the camera)**. Keep this in mind when reading older scripts.

## Directory Structure

```
soarm101/
├── README.md / README_EN.md          # Project documentation (Chinese / English)
├── calibration_data.json              # Dual-arm calibration data (joint limits, offsets, home pose)
├── gripper_calibration.json           # Gripper open/close mapping calibration data
│
├── main/                              # [Core code] calibration, sync, teleoperation, control
├── data_collection/                   # [Data collection] teleop recording, camera capture, VLA inference
├── diagnosis/                         # [Diagnostics] serial/motor/gripper/camera fault detection
├── fix/                               # [Repair] fault clearing, EEPROM unlock, limit restoration
├── tests/                             # [Tests] connectivity / unit tests from development
│
├── grap001/                           # Module: direct single-arm control (register-level protocol)
├── sync/                              # Module: pure-pyserial dual-arm synchronization
├── grasp_vision/                      # Module: OpenCV color-based visual grasping
├── opencv/                            # Module: YOLOv8 visual grasping + camera calibration
│
├── dataset/                           # Teleoperation episode data (JSON)
├── datasets/                          # (spare data directory)
└── camera_recordings/                 # Follower-arm camera recordings (mp4)
```

> **Important — how to run**: All scripts reference data files via relative paths (e.g. `calibration_data.json`, `dataset/`, `camera_recordings/`). **Always run scripts from the project root**, e.g. `python main\sync_and_teleop.py`, rather than `cd`-ing into `main/` first.

## Tech Stack

| Technology | Purpose |
|------------|---------|
| pyserial | Low-level serial communication, direct Feetech STS3215 half-duplex protocol |
| lerobot SDK (`SOFollower`) | High-level robot arm API (calibration, observation, action sending) |
| OpenCV | Video capture, HSV color detection, image display |
| ultralytics YOLOv8 | Object detection (`yolov8n.pt`, torch CUDA accelerated) |
| numpy / scipy | Array math, mapping-function fitting (linear regression / interpolation) |
| websocket + msgpack | Remote VLA server communication (image upload, action download) |
| msvcrt | Non-blocking keyboard input on Windows |

Dependencies (`pip install`):

```
pyserial
numpy
scipy
opencv-python
ultralytics            # YOLOv8 (pulls in torch; this project uses torch 2.5.1+cu121)
lerobot                 # SOFollower SDK (this project uses the so_follower module)
```

## Development Timeline

The project evolved through five stages, each building on the previous one.

| Stage | Time | Work | Code Location |
|-------|------|------|---------------|
| 1. Direct single-arm control | Mid-July | Register-level STS3215 protocol via pyserial, keyboard control, demonstration recording/playback | `grap001/` |
| 2. Dual-arm calibration & teleop | Late July | lerobot SDK calibration, leader-follower sync, episode data collection | `main/`, `data_collection/` |
| 3. Fault diagnosis & repair | Early August | Troubleshooting servo red-LED faults, voltage anomalies, EEPROM lockups | `diagnosis/`, `fix/` |
| 4. Vision-based grasping | Early August | HSV color and YOLOv8 visual-servo grasping, camera calibration | `grasp_vision/`, `opencv/` |
| 5. Remote VLA inference verification | August | End-to-end WebSocket + msgpack verification with a remote VLA service | `data_collection/` |

---

## Code Reference

### 1. main/ — Core Code (19 scripts)

Everyday core functionality: calibration, dual-arm sync, teleoperation, single-arm/gripper control, safety utilities.

**Calibration:**

| Script | Description |
|--------|-------------|
| `calibrate_robot.py` | First-time calibration of a single arm (COM3) via the lerobot CLI |
| `calibrate_and_sync.py` | Connect both arms → calibrate to home → real-time leader-follower sync |
| `calibrate_gripper.py` | Manually record 5 gripper openings (100%/75%/50%/25%/0%) to build the gripper mapping |
| `calibrate_gripper_range.py` | Gripper range calibration |
| `calibrate_with_direction_check.py` | Dual-arm calibration with per-joint direction-consistency checks (prevents mirrored motion) |
| `manual_calibrate.py` | Manual calibration |
| `force_recalibrate.py` / `recalibrate_master.py` | Forced recalibration |
| `create_calibration_from_session.py` | Generate calibration data from a teleoperation session |
| `extract_calibration_data.py` | Extract calibration data |

**Sync & teleoperation:**

| Script | Description |
|--------|-------------|
| `sync_and_teleop.py` | **Recommended entry point**: stepwise position sync at startup (avoids sudden large motions), then teleoperation |
| `sync.py` | Leader-follower sync implemented in pure pyserial (STS3215 register protocol) |
| `smart_mapping.py` | Builds the leader→follower mapping from calibration data via linear regression/interpolation for non-linear compensation; doubles as a serial-port cleanup tool |
| `keyboard_control.py` | Keyboard joint control with an OpenCV visualization window |

**Control & safety:**

| Script | Description |
|--------|-------------|
| `single_arm_control.py` | Single-arm control |
| `control_gripper.py` | Standalone gripper control |
| `ultra_safe.py` | Ultra-safe mode: connect with `calibrate=False` and send a no-op test action |
| `test_torque.py` | Disable torque immediately after connecting both arms, for manual posing |
| `disable_torque.py` | Disable torque |

### 2. data_collection/ — Data Collection (7 scripts)

Teleoperation demonstration recording, camera video capture, and remote VLA inference verification.

| Script | Description |
|--------|-------------|
| `teleop_simple.py` | Basic leader-follower teleoperation that records episode data to `dataset/` |
| `teleop_data_collection.py` | Teleoperation + follower arm pose data collection |
| `record_camera.py` | Follower-arm camera recording (press q to stop; saves mp4 to `camera_recordings/`) |
| `test101.py` | Connect to a remote VLA server via WebSocket, send camera images, receive actions (single-threaded) |
| `test101_multithread.py` | VLA inference verification (multithreaded) |
| `test_simple.py` | VLA inference + direct arm control (simplified, skips handshake) |
| `test_vla_action.py` | VLA action data format verification (msgpack + numpy serialization) |

### 3. diagnosis/ — Diagnostics (25 scripts)

Troubleshooting tools: serial port checks, motor/servo scanning, gripper-specific diagnosis, camera detection, state monitoring.

| Script | Description |
|--------|-------------|
| `check_ports.py` / `check_serial.py` | Serial port checks (routine check before moving joints) |
| `check_bus_methods.py` | Bus communication method checks |
| `check_motors.py` / `check_motors_5v.py` | Motor status checks (latter for the 5 V follower arm) |
| `check_servos.py` / `scan_servos.py` / `detect_motors.py` | Servo/motor scanning |
| `check_gripper_motor.py` / `check_master_gripper.py` | Gripper motor checks |
| `diagnose_state.py` / `diagnose_voltage.py` | Deep state / voltage diagnosis |
| `diagnose_com4_deep.py` / `diag_com3.py` / `diag_correct.py` | Per-port deep diagnosis |
| `diagnose_gripper.py` / `diagnose_gripper_registers.py` | Gripper-specific diagnosis |
| `comprehensive_gripper_diagnosis.py` | Comprehensive gripper diagnosis |
| `diagnose_camera.py` / `detect_cameras.py` / `find_camera.py` | Camera detection |
| `full_diagnosis.py` / `safe_diagnose.py` | Full / safe diagnosis |
| `monitor_com3.py` | Real-time COM3 serial monitor |
| `read_raw_gripper.py` | Raw gripper register reads |

### 4. fix/ — Repair (17 scripts)

Fault repair and recovery tools: fault-latch clearing, red-LED repair, EEPROM unlock, voltage-limit fixes.

| Script | Description |
|--------|-------------|
| `clear_fault.py` / `clear_faults.py` | Clear the fault latch (write 0 to address 48) |
| `fix_led.py` / `fix_all_led.py` | Red-LED flashing repair (`fix_all_led.py` is the final version, works for all servos on both arms) |
| `fix_com3_correct.py` / `fix_com3_undervolt.py` | Follower arm (COM3) repair / undervoltage repair |
| `fix_com4.py` / `fix_com4_correct.py` / `fix_com4_final.py` | Leader arm (COM4) repair iterations |
| `fix_both_arms.py` | Repair both arms at once |
| `fix_voltage_limit.py` / `fix_motor2_voltage.py` | Voltage-limit repair |
| `unlock_follower.py` / `unlock_gripper.py` / `unlock_raw.py` / `deep_unlock_follower.py` | EEPROM unlock series |
| `reconfigure_gripper.py` | Gripper reconfiguration |

### 5. tests/ — Tests (8 scripts)

Connectivity and unit tests written during development.

| Script | Description |
|--------|-------------|
| `test_bus.py` | Bus communication test |
| `test_camera.py` | Camera open test |
| `test_movement.py` | Joint motion test |
| `test_write.py` | Register write test |
| `test_raw_registers.py` | Raw register read/write test |
| `test_follower_range.py` | Follower arm range-of-motion test |
| `safe_test.py` | Safe-mode test |
| `debug_test.py` | Debug test |

### 6. Module Directories (kept as-is)

#### grap001/ — Stage 1: Direct Single-Arm Control

No SDK dependency; the STS3215 protocol is implemented directly with pyserial (packet format: `0xFF 0xFF [ID] [Length] [Instruction] [Params...] [Checksum]`).

- `arm_controller.py`: core controller class `SoArmController` (register read/write, sync write, smooth motion);
- `keyboard_control.py`: keyboard joint control;
- `record_positions.py` / `positions.json`: manual posing and key-position recording;
- `grasp.py`: executes the 7-step grasp sequence `home → pre_grasp → grasp_close → grasp_up → place → place_release → home`;
- `record_replay.py`: 20 Hz motion recording with frame-by-frame playback (exact replication) and smoothed playback (interpolated);
- `records/`: recorded motion trajectories.

See [`grap001/README.md`](grap001/README.md) for details.

#### sync/ — Stage 2: Pure-pyserial Dual-Arm Sync Module

- `sync_controller.py`: sync controller (offsets + scale compensation);
- `sync_run.py`: leader-follower sync launcher.

#### grasp_vision/ — Stage 4a: OpenCV Color-Based Visual Grasping

- `arm_controller.py`: lerobot SOFollower wrapper (safety limits);
- `object_detector.py`: HSV color detection (red/blue/green/yellow + contour filtering);
- `grasp_main.py`: visual grasping main program (manual/auto modes).

#### opencv/ — Stage 4b: YOLOv8 Visual Grasping + Camera Calibration (final vision solution)

- `yolo_detect.py`: real-time YOLOv8n detection (80 COCO classes, GPU accelerated);
- `yolo_grasp.py`: YOLO visual-servo grasping (background thread + every-other-frame inference + servo fine alignment + descend-and-grasp);
- `vision_grasp.py`: HSV color visual-servo grasping (GPU-free alternative implementation);
- `calibrate.py`: pixel coordinate → joint angle calibration;
- `setup_search.py`: search-pose calibration (generates `search_poses.json`);
- `yolov8n.pt`: YOLOv8n pretrained model.

---

## Quick Start

### 1. Install dependencies

```bash
pip install pyserial numpy scipy opencv-python ultralytics lerobot
```

### 2. Typical Workflows

**Leader-follower teleoperation (demonstration data collection):**

```bash
python diagnosis\check_ports.py       # 1. Check serial ports (if this fails, run smart_mapping.py as admin; if still failing, reboot)
python main\sync_and_teleop.py       # 2. Sync both arms, then start teleoperation
```

**Vision-based autonomous grasping (YOLO version):**

```bash
cd opencv
python setup_search.py                # First time: calibrate search poses (generates search_poses.json)
python calibrate.py                   # First time: pixel-to-joint-angle calibration
python yolo_grasp.py                  # Run autonomous grasping
```

**Data collection & VLA inference:**

```bash
python data_collection\teleop_data_collection.py   # Teleoperation + episode collection
python data_collection\record_camera.py            # Camera recording
python data_collection\test101.py                  # Remote VLA inference verification
```

**Single-arm demonstration recording & playback (early approach):**

```bash
cd grap001
python record_replay.py record grasp_demo   # Record
python record_replay.py smooth grasp_demo  # Smoothed playback
```

## Safety Notes

1. **Write operations are only allowed on SRAM registers (addresses 40, 41, 48, 42)**; do not modify EEPROM (addresses 9–39, 55) or any permanently stored hardware configuration, unless explicitly following the repair procedure;
2. Make sure the arm's workspace is clear before running;
3. Before replay/teleoperation, confirm both arms start near the recorded/home pose to avoid large jumps;
4. Press Ctrl+C in an emergency — scripts disable torque on exit;
5. A serial port can only be used by one script at a time;
6. Verify the voltage rating before first power-on (leader arm 12 V servos / follower arm 7.4 V servos); wrong supply voltage triggers over-voltage protection (red LED).

## Data Output Directories

| Directory | Contents |
|-----------|----------|
| `dataset/` | Teleoperation episode joint data (JSON) |
| `camera_recordings/` | Follower-arm camera videos (640×480 @ 30 fps, mp4; generated locally, not committed) |
| `grap001/records/` | Single-arm demonstration recordings |
| `calibration_data.json` | Dual-arm joint calibration data (with backups) |
| `gripper_calibration.json` | Gripper opening mapping data |
