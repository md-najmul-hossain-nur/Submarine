# Submarine Project — Website + Auto/Manual Control Overview

এই README টিতে পুরো প্রজেক্টের সারাংশ আছে — কী‑কী হোবে হার্ডওয়্যার/সফটওয়্যার দিক থেকে, ওয়েবসাইটে কি কি পেজ ও বোতাম থাকবে, Auto (machine‑learning) মোডের ধারণা ও কাজের ধারা, Manual মোড কীভাবে কাজ করবে, সেফটি‑ফিচার, লগিং ও ডেপ্লয়মেন্ট নোট ইত্যাদি। কোড নেই — কেবল ডিজাইন/ফিচার স্পেসিফিকেশন ও অপারেশনাল নির্দেশিকা (বাংলায়)।

সংক্ষিপ্ত সারমর্ম
- লক্ষ্য: 1.5 m সাবমেরিনের জন্য একটি ওয়েব ইন্টারফেস যেখানে অপারেটর লাইভ ভিডিও ও টেলিমেট্রি দেখবে, ম্যানুয়ালি কন্ট্রোল করবে বা একটি ML‑চালিত Auto মোড অন করে সাবকে স্বয়ংক্রিয় কাজ করাবে। সব সময় হার্ডওয়্যার kill‑switch ও safety overrides থাকবে।

1 — Project Components (সংক্ষেপ)
- Hardware (তুমি যা আছে বলেছো)
  - Raspberry Pi 5 + Pi Camera (video)  
  - MCU (Arduino/ESP32) → servos (servo 996 ×3) + ESC/motor  
  - Sensors: MPU‑9250 (IMU), BMP280 (internal), DS18B20 (water temp), SEN0189 (turbidity), GL5537 (LDR), INA219 or voltage divider (battery V/I), leak sensor, JSN‑SR04T (air proximity)  
  - Hull: sealed electronics bay, bulkhead glands, prop shaft + lip seal  
- Software
  - Pi agent: camera stream + telemetry publisher + bridge to MCU  
  - Central server / VPS: web server + WebSocket broker (telemetry & commands)  
  - Web UI: live video, telemetry dashboard, manual controls, auto button & status, logs, mission management  
  - ML pipeline (runs on Pi5 or remote server): vision models for automatic decisions

2 — What the Website Will Contain (pages & UI elements)
- Public landing page (project info, mission logs archive—optional)  
- Operator Dashboard (secured): main control surface
  - Live video window (Pi Camera stream)  
  - Telemetry panel (yaw/pitch/roll, battery V/I, water temp, turbidity, leak flag, internal temp)  
  - Manual control widgets:
    - Throttle slider (forward/reverse)  
    - Rudder slider / joystick  
    - Front & rear elevator sliders / trim controls  
    - Individual servo status indicators  
    - „Kill / E‑Stop“ big red button (hardware override as well)  
  - Auto control widgets:
    - Auto Mode ON/OFF big button (toggled, requires operator auth)  
    - Auto‑mode subsettings (select task: "Inspect", "Follow target", "Survey path", "Return to surface")  
    - Auto state display (Idle → Searching → Engaged → Paused → Returning)  
  - Event & Alerts area (leak, low battery, turbidity spike, comms loss)  
  - Logs & recordings: list of recorded video clips (tagged by event), download links, telemetry CSV download  
  - Settings / Admin:
    - PID tuning sliders (heading, pitch)  
    - Thresholds (low battery, turbidity)  
    - User management (viewer / operator)  
- Mission Planner (optional): simple scripted missions (time‑based steps)

3 — Single Big Button: AUTO (behaviour & safety)
- Button semantics:
  - Two‑stage action: (1) ENABLE Auto (arm) — server checks preflight conditions; (2) START Auto (execute) — actual autonomous behavior begins.  
  - Only authorized operators can ARM/START. Visual confirmation & countdown before START.  
  - Auto can be PAUSED or ABORTED anytime; abort triggers immediate motor cutoff and returns to safe manual state.
- Safety prechecks before enabling Auto:
  - Leak == false  
  - Battery voltage > configured threshold  
  - Servos & motor respond in bench test (heartbeat)  
  - Telemetry link healthy (Pi↔Server connected)  
- Auto mode constraints:
  - Auto mode will never disable hardware kill switch — hardware E‑STOP always wins.  
  - Auto will obey soft limits (max throttle, max pitch) configured in UI.  
  - Operator always able to take over immediately (Manual override button or by moving any manual control).

4 — Auto Mode — Machine Learning & Decision Flow (high level)
- Purpose of ML in Auto mode:
  - Improve perception from camera (object detection, target recognition)  
  - Image enhancement / dehaze to improve visibility  
  - Visual decision making for tasks like "approach target", "follow object", "survey and tag turbidity events"
- ML components (where to run)
  - Lightweight models on Pi5:
    - Image enhancement: real‑time denoise / CLAHE / dehaze preprocessor (improves downstream detection)  
    - Object detector (tiny/optimized model e.g., MobileNet SSD, YOLO‑nano or TensorRT optimized) for recognizing markers, buoys, or regions of interest  
    - Simple classifier for "clear vs turbid" frames (combined with SEN0189)  
  - Heavier compute (optional): offload to VPS or cloud for larger models (if latency and connectivity allow).
- Decision/logical pipeline (Auto runtime)
  1. Perception: Pi Camera frames → preprocessing → inference (detection/classification)  
  2. Sensor fusion: combine IMU & turbidity & light levels with vision (e.g., if SEN0189 high then increase cleaning attempt or reduce speed)  
  3. Behavior selection: (state machine)
     - SEARCH: sweep area / hold heading while scanning for target  
     - APPROACH: control pitch & throttle to move toward detected target, use rudder to align  
     - INSPECT: slow forward motion, increase camera frame save rate + tag around target  
     - SURVEY: follow scripted heading/time path and log sensors  
     - RETURN / SURFACE: low battery or leak → stop mission & surface  
  4. Control output: state machine sends high‑level commands to MCU agent (e.g., desired heading/pitch/throttle) → MCU runs PID to actuate servos & ESC
- Event triggers & Auto reactions:
  - turbidity spike (SEN0189): reduce speed, trigger camera cleaning (wiper/purge if installed), record high‑priority clip  
  - leak: abort mission, motor off, surface  
  - proximity alert at surface (JSN): slow & stop approach  
  - stuck / overcurrent: back off & try alternate path / alert operator

5 — Manual Mode (what site will allow)
- Full manual control via UI sliders & joystick. Immediate effect on MCU via WebSocket pipeline.  
- Manual override behavior:
  - If operator moves any manual control while Auto engaged → Auto pauses and control transfers to operator (configurable)  
  - Kill/E‑Stop always immediately cuts motor power (server sends command; hardware kill must cut power directly)

6 — Telemetry & Logging (what is stored & shown)
- Live telemetry on UI: yaw/pitch/roll, battery V/I, water temp, turbidity, leak, internal temp — updated per configured rates  
- Logs per mission (folder):
  - telemetry.csv (timestamped)  
  - tagged video clips (on events & manual save)  
  - config snapshot (PID params & thresholds)  
- Download/Export: mission zip with telemetry + video

7 — Security & Access Control
- Use HTTPS/WSS (TLS). Server must have valid certificate (Let's Encrypt).  
- Authentication:
  - Roles: viewer (only watch), operator (manual control + auto arm), admin (settings)  
  - Use token/JWT for Pi agent authentication and operator sessions.  
- Command authorization & rate limiting (server side checks)  
- Audit logs: user actions (auto start, manual takeover, kill) recorded in admin log

8 — Deployment Notes (minimal)
- Recommended deployment:
  - VPS (Ubuntu) hosting server + nginx + certbot for TLS  
  - Pi5 as agent connecting to VPS over secure WebSocket (WSS) — Pi provides camera stream to server (RTSP/HLS) or server proxies MJPEG  
  - Database: simple mission storage with files & SQLite  
- Testing flow:
  - Local bench test (no prop) → LAN test (ngrok) → VPS staging → pool tethered tests → open field

9 — Pre‑flight Checklist (UI will show this)
- Hatch sealed, O‑ring present  
- Bulkhead glands tightened & pushrods free  
- Battery charged & fuse installed  
- Leak sensor test (wet) → no alarm  
- IMU calibrated & telemetry streaming OK  
- Camera stream visible & recording test clip  
- Servos neutral & ESC calibrated (props off)  
- Auto preconditions satisfied before arming Auto

10 — Operator UX / Buttons on Website (quick reference)
- Connect / Disconnect (top bar)  
- Live video (center)  
- Manual controls:
  - Throttle slider, Rudder slider, Elevator sliders  
  - Servo trim buttons  
  - „Take control“ button (forces Manual takeover)  
- Auto controls:
  - Arm Auto (checks) → Start Auto → Pause Auto → Abort Auto  
  - Auto mode selector dropdown (Inspect / Follow / Survey / Return)  
  - Auto status indicator (color coded)  
- Safety:
  - Big red Kill/E‑Stop (hardware + software)  
  - Alerts panel (clickable items open related video segment & telemetry)

11 — ML Data & Training (brief)
- Data collected on missions:
  - Camera frames (with timestamps) + telemetry & turbidity labels → used to fine‑tune detector/classifier models  
- Suggested ML tasks:
  - Underwater object detection (marker/buoy/target)  
  - Frame quality classifier (good/poor visibility) using labeled turbidity + image metrics  
  - Behavior imitation (recorded manual approaches used to train approach policy — offline)  
- Training workflow:
  - Collect labeled dataset locally, train on workstation or cloud, export optimized model (TensorFlow Lite / ONNX / TensorRT) → deploy to Pi5

12 — Failure modes & limitations (be explicit)
- Vision in turbid water is limited — ML may fail in heavy turbidity. SEN0189 + software fallback required.  
- No reliable underwater obstacle avoidance without sonar (JSN not for underwater). Auto must assume limited obstacle awareness.  
- Depth hold not possible without dedicated depth sensor (MS5837 recommended for future).  
- ML inference latency & Pi5 CPU load: keep models lightweight; consider offloading if latency unacceptable.

13 — Future improvements (roadmap)
- Add depth sensor (MS5837) for depth‑hold  
- Add vertical thruster for hover/station‑keeping  
- Add forward‑looking sonar for obstacle avoidance  
- Implement WebRTC low‑latency video pipeline  
- Improved ML models and automated dataset pipeline

14 — Quick Operational Scenarios (examples)
- Scenario A: Manual inspection
  - Operator opens dashboard → views video → uses manual joystick & throttle to approach point of interest → records clip → logs notes.
- Scenario B: Auto survey
  - Operator arms Auto, selects Survey path, starts Auto → sub follows path, logs turbidity levels → Auto pauses on turbidity spike, records clip, resumes.
- Scenario C: Emergency
  - Leak sensor triggers → Auto aborts, motors cut, sub surfaces; operator notified via UI alert & recorded clip.

15 — Contact / Credits
- Project owner: [Your name / team] (তুমি এখানে নাম রাখবে)  
- Hardware list: Pi5, Pi Camera, MCU (Arduino/ESP32), servos (servo996), sensors (MPU‑9250, BMP280, DS18B20, SEN0189, GL5537, INA219, leak sensor, JSN‑SR04T)  
- If তুমি চাইলে, আমি এই README থেকে ভিত্তি নিয়ে UI mockup, WebSocket message schema এবং Auto behavior flowchart (no code) তৈরী করে দেব।

---

Prepared for: তোমার Submarine Project — Web + Auto/Manual Control  
Prepared by: তোমার সহকারী  
Date: 2025-12-26

python -m venv .venv
.\.venv\Scripts\Activate.ps1