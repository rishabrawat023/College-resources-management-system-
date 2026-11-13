from flask import Flask, render_template, request, jsonify
from pathlib import Path
from datetime import datetime
from functools import wraps
import json
import threading
import uuid

app = Flask(__name__)
DATA_FILE = Path(__file__).with_name("database.json")
LOCK = threading.RLock()

RESOURCE_TYPES = ["Classroom", "Computer Lab", "Seminar Hall", "Auditorium"]
TIME_FORMAT = "%H:%M"

def default_data():
    return {
        "resources": [
            {"id": "R001", "name": "A-Block Room 101", "type": "Classroom", "capacity": 60, "location": "A Block, First Floor", "smartboard": True, "projector": True, "pcs": 0, "ac": True},
            {"id": "R002", "name": "Computer Lab 1", "type": "Computer Lab", "capacity": 40, "location": "IT Block, Ground Floor", "smartboard": False, "projector": True, "pcs": 40, "ac": True},
            {"id": "R003", "name": "Seminar Hall", "type": "Seminar Hall", "capacity": 120, "location": "Admin Block, Second Floor", "smartboard": True, "projector": True, "pcs": 0, "ac": True},
            {"id": "R004", "name": "Main Auditorium", "type": "Auditorium", "capacity": 350, "location": "Central Campus", "smartboard": False, "projector": True, "pcs": 0, "ac": True},
            {"id": "R005", "name": "B-Block Room 204", "type": "Classroom", "capacity": 45, "location": "B Block, Second Floor", "smartboard": False, "projector": True, "pcs": 0, "ac": False}
        ],
        "bookings": [],
        "waiting_list": []
    }

def load_data():
    with LOCK:
        if not DATA_FILE.exists():
            save_data(default_data())
        try:
            with DATA_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            for key in ("resources", "bookings", "waiting_list"):
                data.setdefault(key, [])
            return data
        except (json.JSONDecodeError, OSError):
            backup = DATA_FILE.with_suffix(".corrupt.json")
            try:
                DATA_FILE.replace(backup)
            except OSError:
                pass
            data = default_data()
            save_data(data)
            return data

def save_data(data):
    with LOCK:
        temp = DATA_FILE.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp.replace(DATA_FILE)

def api_error(message, status=400):
    return jsonify({"success": False, "error": message}), status

def parse_slot(date_text, start_text, end_text):
    try:
        day = datetime.strptime(date_text, "%Y-%m-%d").date()
        start = datetime.strptime(start_text, TIME_FORMAT).time()
        end = datetime.strptime(end_text, TIME_FORMAT).time()
        if end <= start:
            raise ValueError("End time must be later than start time.")
        return day, start, end
    except ValueError as exc:
        raise ValueError(str(exc))

def overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end

def slot_conflict(data, resource_id, date_text, start_text, end_text, ignore_booking_id=None):
    for booking in data["bookings"]:
        if booking["resource_id"] != resource_id or booking["date"] != date_text:
            continue
        if ignore_booking_id and booking["id"] == ignore_booking_id:
            continue
        if overlaps(start_text, end_text, booking["start_time"], booking["end_time"]):
            return booking
    return None

def next_id(prefix, items):
    return f"{prefix}{uuid.uuid4().hex[:7].upper()}"

def resource_index(resources):
    # Dictionary/hash table: O(1) average resource lookup by ID.
    return {resource["id"]: resource for resource in resources}

@app.route("/")
def index():
    return render_template("index.html")

@app.get("/api/dashboard")
def dashboard():
    data = load_data()
    counts = {kind: sum(r["type"] == kind for r in data["resources"]) for kind in RESOURCE_TYPES}
    return jsonify({
        "success": True,
        "total_resources": len(data["resources"]),
        "total_bookings": len(data["bookings"]),
        "waiting_count": len(data["waiting_list"]),
        "available_count": max(0, len(data["resources"]) - len({b["resource_id"] for b in data["bookings"]})),
        "type_counts": counts,
        "recent_bookings": sorted(data["bookings"], key=lambda b: (b["date"], b["start_time"]), reverse=True)[:5]
    })

@app.get("/api/resources")
def get_resources():
    data = load_data()
    query = request.args.get("q", "").strip().lower()
    kind = request.args.get("type", "").strip()
    sort_by = request.args.get("sort", "name")
    # Linear Search: scan each resource and match query fields.
    results = []
    for r in data["resources"]:
        searchable = " ".join(str(r.get(k, "")) for k in ("id", "name", "type", "location")).lower()
        if (not query or query in searchable) and (not kind or r["type"] == kind):
            results.append(r)
    # Sorting: Python's stable Timsort.
    if sort_by == "capacity":
        results.sort(key=lambda r: int(r.get("capacity", 0)), reverse=True)
    else:
        results.sort(key=lambda r: r.get("name", "").lower())
    return jsonify({"success": True, "resources": results})

@app.post("/api/resources")
def add_resource():
    payload = request.get_json(silent=True) or {}
    required = ["name", "type", "capacity", "location"]
    if any(not str(payload.get(k, "")).strip() for k in required):
        return api_error("Please complete all required resource fields.")
    if payload["type"] not in RESOURCE_TYPES:
        return api_error("Invalid resource type.")
    try:
        capacity = int(payload["capacity"])
        pcs = int(payload.get("pcs", 0) or 0)
        if capacity < 1 or pcs < 0:
            raise ValueError()
    except (TypeError, ValueError):
        return api_error("Capacity must be at least 1 and PCs cannot be negative.")
    data = load_data()
    resource = {
        "id": next_id("R", data["resources"]), "name": payload["name"].strip(),
        "type": payload["type"], "capacity": capacity, "location": payload["location"].strip(),
        "smartboard": bool(payload.get("smartboard")), "projector": bool(payload.get("projector")),
        "pcs": pcs, "ac": bool(payload.get("ac"))
    }
    data["resources"].append(resource)
    save_data(data)
    return jsonify({"success": True, "resource": resource}), 201

@app.put("/api/resources/<resource_id>")
def update_resource(resource_id):
    payload = request.get_json(silent=True) or {}
    data = load_data()
    index = resource_index(data["resources"])
    resource = index.get(resource_id)
    if not resource:
        return api_error("Resource not found.", 404)
    if payload.get("type", resource["type"]) not in RESOURCE_TYPES:
        return api_error("Invalid resource type.")
    try:
        capacity = int(payload.get("capacity", resource["capacity"]))
        pcs = int(payload.get("pcs", resource["pcs"]))
        if capacity < 1 or pcs < 0:
            raise ValueError()
    except (TypeError, ValueError):
        return api_error("Capacity must be at least 1 and PCs cannot be negative.")
    resource.update({
        "name": str(payload.get("name", resource["name"])).strip(),
        "type": payload.get("type", resource["type"]), "capacity": capacity,
        "location": str(payload.get("location", resource["location"])).strip(),
        "smartboard": bool(payload.get("smartboard", resource["smartboard"])),
        "projector": bool(payload.get("projector", resource["projector"])),
        "pcs": pcs, "ac": bool(payload.get("ac", resource["ac"]))
    })
    save_data(data)
    return jsonify({"success": True, "resource": resource})

@app.delete("/api/resources/<resource_id>")
def delete_resource(resource_id):
    data = load_data()
    if not any(r["id"] == resource_id for r in data["resources"]):
        return api_error("Resource not found.", 404)
    if any(b["resource_id"] == resource_id for b in data["bookings"]) or any(w["resource_id"] == resource_id for w in data["waiting_list"]):
        return api_error("Cannot delete this resource while it has active bookings or waiting-list entries.")
    data["resources"] = [r for r in data["resources"] if r["id"] != resource_id]
    save_data(data)
    return jsonify({"success": True})

@app.get("/api/bookings")
def get_bookings():
    data = load_data()
    return jsonify({"success": True, "bookings": sorted(data["bookings"], key=lambda b: (b["date"], b["start_time"]))})

@app.post("/api/bookings")
def create_booking():
    payload = request.get_json(silent=True) or {}
    for key in ("resource_id", "booked_by", "purpose", "date", "start_time", "end_time"):
        if not str(payload.get(key, "")).strip():
            return api_error(f"{key.replace('_', ' ').capitalize()} is required.")
    try:
        parse_slot(payload["date"], payload["start_time"], payload["end_time"])
    except ValueError as exc:
        return api_error(str(exc))
    data = load_data()
    resource = resource_index(data["resources"]).get(payload["resource_id"])
    if not resource:
        return api_error("Selected resource does not exist.", 404)
    conflict = slot_conflict(data, payload["resource_id"], payload["date"], payload["start_time"], payload["end_time"])
    booking = {
        "id": next_id("B", data["bookings"]), "resource_id": payload["resource_id"],
        "resource_name": resource["name"], "booked_by": payload["booked_by"].strip(),
        "purpose": payload["purpose"].strip(), "date": payload["date"],
        "start_time": payload["start_time"], "end_time": payload["end_time"]
    }
    if conflict:
        # FIFO queue: append to the end; earlier entries retain priority.
        waiting = {
            "id": next_id("W", data["waiting_list"]), **booking,
            "requested_at": datetime.now().isoformat(timespec="seconds")
        }
        data["waiting_list"].append(waiting)
        save_data(data)
        return jsonify({"success": True, "status": "waiting", "message": "Time slot is occupied. Added to the FIFO waiting list.", "waiting": waiting}), 201
    data["bookings"].append(booking)
    save_data(data)
    return jsonify({"success": True, "status": "booked", "booking": booking}), 201

def promote_waiting(data, resource_id):
    # FIFO promotion: inspect in insertion order and promote the first currently conflict-free request.
    for waiting in list(data["waiting_list"]):
        if waiting["resource_id"] != resource_id:
            continue
        if not slot_conflict(data, resource_id, waiting["date"], waiting["start_time"], waiting["end_time"]):
            data["waiting_list"].remove(waiting)
            booking = {k: waiting[k] for k in ("resource_id", "resource_name", "booked_by", "purpose", "date", "start_time", "end_time")}
            booking["id"] = next_id("B", data["bookings"])
            data["bookings"].append(booking)
            return booking
    return None

@app.delete("/api/bookings/<booking_id>")
def cancel_booking(booking_id):
    data = load_data()
    booking = next((b for b in data["bookings"] if b["id"] == booking_id), None)
    if not booking:
        return api_error("Booking not found.", 404)
    data["bookings"].remove(booking)
    promoted = promote_waiting(data, booking["resource_id"])
    save_data(data)
    return jsonify({"success": True, "promoted": promoted, "message": "Booking cancelled." + (" The first eligible waiting request has been confirmed." if promoted else "")})

@app.get("/api/waiting-list")
def get_waiting():
    data = load_data()
    return jsonify({"success": True, "waiting_list": data["waiting_list"]})

@app.delete("/api/waiting-list/<waiting_id>")
def cancel_waiting(waiting_id):
    data = load_data()
    item = next((w for w in data["waiting_list"] if w["id"] == waiting_id), None)
    if not item:
        return api_error("Waiting-list entry not found.", 404)
    data["waiting_list"].remove(item)
    save_data(data)
    return jsonify({"success": True})

@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return api_error("API endpoint not found.", 404)
    return "Page not found", 404

@app.errorhandler(500)
def server_error(_):
    return api_error("Unexpected server error. Check the terminal for details.", 500)

if __name__ == "__main__":
    load_data()
    app.run(debug=True, host="127.0.0.1", port=5000)
