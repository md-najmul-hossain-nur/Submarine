# Autonomous and Manual ROV Submarine Project

---

## 📚 Overview

This repository documents the system design and concept of an advanced Remote Operated Vehicle (ROV) Submarine that supports both autonomous and manual (operator-directed) underwater operation. The platform provides robust safety, live video and sensor telemetry, flexible mission control, and a modern web-based dashboard for real-time interaction.

This README is designed as the primary reference for academic, research, and demonstration use.  
*No source code is provided in this repository.*

---

## 🚢 Project Objective

To design and develop a 1.5-meter ROV submarine for underwater inspection, monitoring, research, and survey applications.  
The system enables **hybrid operation**:  
- **Autonomous Mode:** Execute scripted missions, intelligent navigation, and auto-responses to environmental conditions.  
- **Manual Mode:** Full operator control and emergency override via a secure web interface — at any time, for ultimate reliability.

The vehicle architecture emphasizes **safety, reliability, and flexibility** across all mission profiles.

---

## 🌐 Key Features

- **Dual-mode hybrid control:** Autonomous missions with instant manual override
- **Web-based dashboard:** Real-time control and monitoring from any browser
- **Live video streaming:** Underwater camera with synchronized sensor telemetry
- **Robust safety:** Hardware/software kill switch, leak detection, battery health monitoring
- **Mission logging:** Time-aligned video and telemetry data export (JSON, CSV)
- **Seamless mode switching:** Operator can take over instantly for safe piloting

---

## 🛠 System Architecture

The architecture is composed of two main layers:

### High-Level Control (Onboard Computer)
- **Raspberry Pi 5**
  - Autonomous logic, ML/AI decision-making (optional)
  - Video streaming and camera control
  - Logging of mission data
  - Secure communication with backend and low-level controller (MCU)
  - Web dashboard host (dashboard may run locally or on a cloud backend)

### Low-Level Control (Microcontroller)
- **Arduino / ESP32**
  - Real-time motor and servo (rudder/elevators) control via PWM
  - Fast sensor acquisition and input filtering
  - Direct hardware safety enforcement (e.g., leak/motor cut)
  - Serial link with Raspberry Pi

### Data & Control Flow
- **Serial or UART** between Pi and MCU for high-speed telemetry and commands
- **WiFi / 4G / LTE** for remote operation and data streaming
- **Web dashboard** accessed via modern browser (mobile/desktop)

---

## 🖥 Hardware Components

**Main Controllers:**
- Raspberry Pi 5 (high-level, Linux-capable)
- Arduino / ESP32 (realtime, low-level)

**Sensors:**
- **MPU-9250:** IMU — orientation (yaw, pitch, roll)
- **BMP280:** Internal temperature & pressure (for environmental and electronics health)
- **DS18B20:** Water temperature (environmental monitoring)
- **SEN0189:** Turbidity sensor (water clarity/cloudiness)
- **GL5537:** Ambient light (environmental + system adaptation)
- **INA219:** Battery voltage/current monitoring (or voltage divider as fallback)
- **JSN-SR04T:** Proximity detection (for docking/surface, air only)
- **Leak sensor:** Immediate water ingress alert

**Actuation:**
- Brushless motor with ESC (main propulsion)
- Three MG996/MG996R servo motors (rudder, front elevator, rear elevator)

**Mechanical:**
- Sealed cylindrical hull (1.5m)
- O-ring sealed removable hatch (for maintenance)
- Pushrod bulkhead glands (for waterproof servo actuation)
- Propeller shaft seal (leak prevention)

---

## ⚡ Control Modes

### Autonomous Mode
- Executes pre-scripted survey, inspection, or waypoint missions
- Uses live sensor feedback for heading, pitch, and environment awareness
- Takes safety or abort actions automatically (e.g., leak, battery low)
- Runs onboard AI/logic on Pi with real-time action via MCU

### Manual Mode
- Direct live control by operator (throttle, steering, trim, etc.) via web dashboard
- Used for testing, fine maneuvering, emergencies, or overriding autonomy

### Seamless Mode Switching
- Manual control and emergency overrides are always available and have the highest priority
- Operator can instantly pause/abort autonomous missions and regain control

---

## 🌐 Web Dashboard

Accessible via secure login from any browser. Key components:

- **Live Camera Feed:** Real-time underwater video
- **Telemetry Panel:** Yaw, pitch, roll; battery status; water & internal temp; turbidity; ambient light; leak status
- **Manual Controls:** Throttle, rudder, elevator trim (sliders/joystick)
- **Auto Mode Panel:** Start/stop autonomous missions, monitor status, set task parameters
- **Alerts & Warnings:** Leak, battery, connection, system faults (with visual/audio notification)
- **Mission Log/Export:** Video archive with synchronized telemetry, downloadable CSV/JSON

---

## 📊 Telemetry & Data Logging

- **Logging format:** Time-aligned data in JSON and CSV per mission
- **Core parameters:**
  - Orientation (yaw, pitch, roll)
  - Battery voltage and current
  - Water and internal temperature
  - Turbidity (water clarity)
  - Ambient light (LDR value)
  - Leak status, proximity readings
  - Auto/manual mode flag, mission/task flag
- **Synchronized Video:** All data is timestamped for exact analysis and review

---

## 🛡 Safety Features

- **Hardware/software kill switch** for immediate shutdown
- **Leak detection** with instant motor/prop cutoff and surfacing action
- **Low battery detection:** Alerts & auto-surface on threshold
- **Sensor or comms loss:** Emergency failsafe actions
- **Continuous manual override:** Operator in full control at any time
- **Encrypted, authenticated communication:** HTTPS/WSS and role-based access

---

## 🚀 Deployment

- **Onboard:** Raspberry Pi 5 runs telemetry, camera streaming, ML/AI, and runs a web client/agent
- **MCU:** Arduino/ESP32 manages actuation and all sensor polling
- **Backend (Planned):** Node.js or Flask application on cloud/VPS server (for multi-user support, enhanced UI)
- **Client:** Any HTML5-capable browser (desktop/mobile)
- **Streaming:** Secure, low-latency MJPEG/RTSP/WebRTC pipeline depending on bandwidth and setup

---

## 🔁 Typical Operation Flow

1. Operator authenticates via web dashboard
2. System performs health/self-check (battery, sensors, comms, camera)
3. Manual test: controls & video verified
4. Autonomous mode enabled, mission started (optional)
5. Live monitoring: video, telemetry, alerts
6. Manual override or mission completion
7. Mission data review — video and log export

---

## 🔮 Future Enhancements

- Depth-hold and enhanced vertical control (e.g., MS5837 depth sensor, vertical thruster)
- Forward-looking sonar for obstacle avoidance
- Smarter autonomous missions and adaptive coverage
- Machine learning for real-time visual analysis, advanced environment mapping, event tagging
- WebRTC or SFU-based video for near-zero-latency control
- Multi-user monitoring, public mission live streaming

---
