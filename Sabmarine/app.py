import os
import random
import threading
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

DB_PATH = os.environ.get("SUBMARINE_DB_PATH", "submarine.db")
OPERATOR_TOKEN = os.environ.get("OPERATOR_TOKEN")
UPLOAD_DIR = os.path.join("static", "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.update(
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{DB_PATH}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

CORS(app)
db = SQLAlchemy(app)


class Mission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(40), default="planned")
    mode = db.Column(db.String(40), default="manual")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Telemetry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.Integer, db.ForeignKey("mission.id"), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    yaw = db.Column(db.Float)
    pitch = db.Column(db.Float)
    roll = db.Column(db.Float)
    battery_v = db.Column(db.Float)
    battery_i = db.Column(db.Float)
    water_temp = db.Column(db.Float)
    turbidity = db.Column(db.Float)
    leak = db.Column(db.Boolean, default=False)
    internal_temp = db.Column(db.Float)


class EventLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.Integer, db.ForeignKey("mission.id"), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(20), default="info")
    message = db.Column(db.String(255))


class VideoClip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.Integer, db.ForeignKey("mission.id"), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    label = db.Column(db.String(120))
    url = db.Column(db.String(255))


class AutoState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_enabled = db.Column(db.Boolean, default=False)
    phase = db.Column(db.String(40), default="idle")
    task = db.Column(db.String(40), default="inspect")
    note = db.Column(db.String(255), default="")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ManualCommand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    command = db.Column(db.String(255))
    payload = db.Column(db.JSON)


class TargetImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.Integer, db.ForeignKey("mission.id"), nullable=True)
    label = db.Column(db.String(120))
    filename = db.Column(db.String(255))
    url = db.Column(db.String(255))
    status = db.Column(db.String(40), default="pending")  # pending | matched
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    matched_at = db.Column(db.DateTime, nullable=True)


def require_operator_token():
    if not OPERATOR_TOKEN:
        return None
    if request.headers.get("X-Operator-Token") == OPERATOR_TOKEN:
        return None
    return jsonify({"error": "unauthorized"}), 401


def seed_demo_data():
    if Mission.query.count() == 0:
        mission = Mission(name="Bench Test", status="active", mode="manual")
        db.session.add(mission)
        db.session.commit()
    else:
        mission = Mission.query.first()

    if AutoState.query.count() == 0:
        db.session.add(AutoState(is_enabled=False, phase="idle", task="inspect"))
        db.session.commit()

    if EventLog.query.count() == 0:
        events = [
            EventLog(message="System boot complete", level="info"),
            EventLog(message="Telemetry link nominal", level="info"),
            EventLog(message="Leak sensor test passed", level="info"),
        ]
        db.session.add_all(events)
        db.session.commit()

    if Telemetry.query.count() == 0:
        now = datetime.utcnow()
        samples = []
        for i in range(30):
            ts = now - timedelta(seconds=30 - i)
            samples.append(
                Telemetry(
                    mission_id=mission.id,
                    timestamp=ts,
                    yaw=random.uniform(-3, 3),
                    pitch=random.uniform(-2, 2),
                    roll=random.uniform(-2, 2),
                    battery_v=15.8 + random.uniform(-0.4, 0.1),
                    battery_i=3.5 + random.uniform(-1, 1),
                    water_temp=21.0 + random.uniform(-1, 1),
                    turbidity=0.2 + random.uniform(0, 0.4),
                    leak=False,
                    internal_temp=32.0 + random.uniform(-1, 1),
                )
            )
        db.session.add_all(samples)
        db.session.commit()

    if VideoClip.query.count() == 0:
        clips = [
            VideoClip(label="Startup test", url="https://example.com/startup.mp4"),
            VideoClip(label="Turbidity spike", url="https://example.com/turbidity.mp4"),
        ]
        db.session.add_all(clips)
        db.session.commit()

    if TargetImage.query.count() == 0:
        # Seed removed per request; leave empty.
        pass


def start_demo_stream(app):
    def generate():
        with app.app_context():
            mission = Mission.query.first()
            if not mission:
                return

            base_last = Telemetry.query.order_by(Telemetry.timestamp.desc()).first()
            yaw = (base_last.yaw if base_last else 0) + random.uniform(-0.4, 0.4)
            pitch = (base_last.pitch if base_last else 0) + random.uniform(-0.3, 0.3)
            roll = (base_last.roll if base_last else 0) + random.uniform(-0.3, 0.3)
            leak_flag = random.random() < 0.01
            turbidity = max(0, (base_last.turbidity if base_last else 0.3) + random.uniform(-0.05, 0.08))

            sample = Telemetry(
                mission_id=mission.id,
                yaw=yaw,
                pitch=pitch,
                roll=roll,
                battery_v=max(14.5, (base_last.battery_v if base_last else 15.8) - random.uniform(0, 0.01)),
                battery_i=max(0.5, 3.0 + random.uniform(-2, 3)),
                water_temp=21.5 + random.uniform(-0.4, 0.4),
                turbidity=turbidity,
                leak=leak_flag,
                internal_temp=32.0 + random.uniform(-0.2, 0.4),
            )
            db.session.add(sample)

            if leak_flag:
                db.session.add(EventLog(level="critical", message="Leak detected in demo stream"))
            db.session.commit()
        timer = threading.Timer(1.5, generate)
        timer.daemon = True
        timer.start()

    generate()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})


@app.route("/api/config")
def config():
    cfg = {
        "battery_low_v": 14.6,
        "turbidity_max": 1.0,
        "soft_limits": {"max_pitch": 20, "max_throttle": 0.7},
        "roles": ["viewer", "operator", "admin"],
    }
    return jsonify(cfg)


@app.route("/api/missions", methods=["GET", "POST"])
def missions():
    if request.method == "POST":
        auth = require_operator_token()
        if auth:
            return auth
        data = request.get_json(force=True)
        mission = Mission(name=data.get("name", "Untitled Mission"), status=data.get("status", "planned"), mode=data.get("mode", "manual"))
        db.session.add(mission)
        db.session.add(EventLog(mission_id=mission.id, level="info", message=f"Mission created: {mission.name}"))
        db.session.commit()
    all_missions = Mission.query.order_by(Mission.created_at.desc()).all()
    return jsonify([
        {
            "id": m.id,
            "name": m.name,
            "status": m.status,
            "mode": m.mode,
            "created_at": m.created_at.isoformat(),
        }
        for m in all_missions
    ])


@app.route("/api/missions/<int:mission_id>", methods=["DELETE"])
def delete_mission(mission_id):
    auth = require_operator_token()
    if auth:
        return auth
    mission = Mission.query.get(mission_id)
    if not mission:
        return jsonify({"error": "not found"}), 404
    # Soft-delete approach: log and remove; for demo no cascade clean-up implemented.
    db.session.add(EventLog(level="warn", message=f"Mission deleted: {mission.name}"))
    db.session.delete(mission)
    db.session.commit()
    return jsonify({"status": "deleted", "id": mission_id})


@app.route("/api/telemetry/latest")
def latest_telemetry():
    limit = min(int(request.args.get("limit", 50)), 500)
    items = Telemetry.query.order_by(Telemetry.timestamp.desc()).limit(limit).all()
    payload = [
        {
            "timestamp": t.timestamp.isoformat(),
            "yaw": t.yaw,
            "pitch": t.pitch,
            "roll": t.roll,
            "battery_v": t.battery_v,
            "battery_i": t.battery_i,
            "water_temp": t.water_temp,
            "turbidity": t.turbidity,
            "leak": t.leak,
            "internal_temp": t.internal_temp,
        }
        for t in reversed(items)
    ]
    return jsonify(payload)


@app.route("/api/telemetry", methods=["POST"])
def ingest_telemetry():
    auth = require_operator_token()
    if auth:
        return auth
    data = request.get_json(force=True)
    mission = Mission.query.first()
    entry = Telemetry(
        mission_id=data.get("mission_id", mission.id if mission else None),
        yaw=data.get("yaw"),
        pitch=data.get("pitch"),
        roll=data.get("roll"),
        battery_v=data.get("battery_v"),
        battery_i=data.get("battery_i"),
        water_temp=data.get("water_temp"),
        turbidity=data.get("turbidity"),
        leak=data.get("leak", False),
        internal_temp=data.get("internal_temp"),
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({"status": "saved", "id": entry.id})


@app.route("/api/events", methods=["GET", "POST"])
def events():
    if request.method == "POST":
        auth = require_operator_token()
        if auth:
            return auth
        data = request.get_json(force=True)
        entry = EventLog(
            mission_id=data.get("mission_id"),
            level=data.get("level", "info"),
            message=data.get("message", ""),
        )
        db.session.add(entry)
        db.session.commit()
    limit = min(int(request.args.get("limit", 30)), 200)
    rows = EventLog.query.order_by(EventLog.timestamp.desc()).limit(limit).all()
    return jsonify([
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "level": e.level,
            "message": e.message,
            "mission_id": e.mission_id,
        }
        for e in reversed(rows)
    ])


@app.route("/api/events/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    auth = require_operator_token()
    if auth:
        return auth
    evt = EventLog.query.get(event_id)
    if not evt:
        return jsonify({"error": "not found"}), 404
    db.session.delete(evt)
    db.session.commit()
    return jsonify({"status": "deleted", "id": event_id})


@app.route("/api/events", methods=["DELETE"])
def delete_events_all():
    auth = require_operator_token()
    if auth:
        return auth
    db.session.query(EventLog).delete()
    db.session.commit()
    return jsonify({"status": "deleted_all"})


@app.route("/api/video-clips", methods=["GET"])
def video_clips():
    rows = VideoClip.query.order_by(VideoClip.timestamp.desc()).all()
    return jsonify([
        {
            "id": v.id,
            "timestamp": v.timestamp.isoformat(),
            "label": v.label,
            "url": v.url,
            "mission_id": v.mission_id,
        }
        for v in rows
    ])


@app.route("/api/video-clips/<int:clip_id>", methods=["DELETE"])
def delete_clip(clip_id):
    auth = require_operator_token()
    if auth:
        return auth
    clip = VideoClip.query.get(clip_id)
    if not clip:
        return jsonify({"error": "not found"}), 404
    db.session.delete(clip)
    db.session.commit()
    return jsonify({"status": "deleted", "id": clip_id})


@app.route("/api/video-clips", methods=["DELETE"])
def delete_clips_all():
    auth = require_operator_token()
    if auth:
        return auth
    db.session.query(VideoClip).delete()
    db.session.commit()
    return jsonify({"status": "deleted_all"})


@app.route("/api/targets", methods=["GET"])
def targets():
    rows = TargetImage.query.order_by(TargetImage.created_at.desc()).all()
    return jsonify([
        {
            "id": t.id,
            "mission_id": t.mission_id,
            "label": t.label,
            "url": t.url,
            "status": t.status,
            "created_at": t.created_at.isoformat(),
            "matched_at": t.matched_at.isoformat() if t.matched_at else None,
        }
        for t in rows
    ])


@app.route("/api/targets/<int:target_id>", methods=["DELETE"])
def delete_target(target_id):
    auth = require_operator_token()
    if auth:
        return auth
    target = TargetImage.query.get(target_id)
    if not target:
        return jsonify({"error": "not found"}), 404
    db.session.delete(target)
    db.session.commit()
    return jsonify({"status": "deleted", "id": target_id})


@app.route("/api/targets/upload", methods=["POST"])
def upload_target():
    auth = require_operator_token()
    if auth:
        return auth
    if "image" not in request.files:
        return jsonify({"error": "missing file"}), 400
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "empty filename"}), 400
    safe_name = secure_filename(file.filename)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    fname = f"{ts}_{safe_name}"
    save_path = os.path.join(UPLOAD_DIR, fname)
    file.save(save_path)

    mission_id = request.form.get("mission_id")
    label = request.form.get("label") or safe_name
    url = f"/static/uploads/{fname}"
    target = TargetImage(mission_id=mission_id, label=label, filename=fname, url=url, status="pending")
    db.session.add(target)
    db.session.add(EventLog(mission_id=mission_id, level="info", message=f"Target image uploaded: {label}"))
    db.session.commit()
    return jsonify({"status": "uploaded", "id": target.id, "url": url})


@app.route("/api/targets/<int:target_id>/match", methods=["POST"])
def match_target(target_id):
    auth = require_operator_token()
    if auth:
        return auth
    target = TargetImage.query.get(target_id)
    if not target:
        return jsonify({"error": "not found"}), 404
    target.status = "matched"
    target.matched_at = datetime.utcnow()
    db.session.add(target)
    db.session.add(EventLog(mission_id=target.mission_id, level="info", message=f"Target matched: {target.label}"))
    db.session.commit()
    return jsonify({"status": "matched", "id": target.id})


@app.route("/api/auto/state", methods=["GET", "POST"])
def auto_state():
    state = AutoState.query.first()
    if request.method == "POST":
        auth = require_operator_token()
        if auth:
            return auth
        data = request.get_json(force=True)
        if not state:
            state = AutoState()
            db.session.add(state)
        state.is_enabled = bool(data.get("is_enabled", state.is_enabled))
        state.phase = data.get("phase", state.phase)
        state.task = data.get("task", state.task)
        state.note = data.get("note", state.note)
        state.updated_at = datetime.utcnow()
        db.session.add(EventLog(level="info", message=f"Auto state updated → enabled={state.is_enabled}, phase={state.phase}", mission_id=data.get("mission_id")))
        db.session.commit()
    if not state:
        return jsonify({"is_enabled": False, "phase": "idle", "task": "inspect", "note": ""})
    return jsonify(
        {
            "is_enabled": state.is_enabled,
            "phase": state.phase,
            "task": state.task,
            "note": state.note,
            "updated_at": (state.updated_at or datetime.utcnow()).isoformat(),
        }
    )


@app.route("/api/commands/manual", methods=["POST"])
def manual_command():
    auth = require_operator_token()
    if auth:
        return auth
    data = request.get_json(force=True)
    cmd = data.get("command", "manual")
    entry = ManualCommand(command=cmd, payload=data)
    db.session.add(entry)
    db.session.add(EventLog(level="info", message=f"Manual command: {cmd}"))
    db.session.commit()
    return jsonify({"status": "accepted", "command": cmd})


@app.route("/api/logs")
def logs():
    mission_id = request.args.get("mission_id")
    query = EventLog.query
    if mission_id:
        query = query.filter_by(mission_id=mission_id)
    rows = query.order_by(EventLog.timestamp.desc()).limit(100).all()
    return jsonify([
        {
            "timestamp": e.timestamp.isoformat(),
            "level": e.level,
            "message": e.message,
        }
        for e in reversed(rows)
    ])


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(500)
def server_error(err):
    return jsonify({"error": "server error", "detail": str(err)}), 500


with app.app_context():
    db.create_all()
    seed_demo_data()
    start_demo_stream(app)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
