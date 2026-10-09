"""
app.py
------
Main Flask file: routes (web pages) + the simple DSA logic.
All SQL is in database.py.

Where DSA is used in this file:
  - Searching    : search_resources()       (linear search with filters)
  - Sorting      : sort_resources()         (sorted() with a key function)
  - Dictionary   : build_resource_dict()    (fast lookup by resource_id)
  - Queue        : waiting_queue            (FIFO waiting list, collections.deque)
  - Recommend    : recommend_resource()     (filter + sort by closest capacity)
"""

import os
from collections import deque
from datetime import datetime, date

import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from markupsafe import escape

import database

app = Flask(__name__)
# Needed by flash() messages. You can set SECRET_KEY in .env if you like.
app.secret_key = os.getenv("SECRET_KEY", "campus-optimizer-dev-key")

RESOURCE_TYPES = ["Classroom", "Computer Lab", "Seminar Hall", "Auditorium"]
STATUS_LIST = ["Available", "Maintenance"]


# ============================================================
# DSA PART 1: Dictionary / Hash Table
# ============================================================
def build_resource_dict(resources):
    """
    Turn the list of resources into a dictionary: {resource_id: resource}.
    Looking up a key in a dictionary takes the same short time
    no matter how many resources there are (hash table).
    """
    resources_by_id = {}
    for resource in resources:
        resources_by_id[resource["resource_id"]] = resource
    return resources_by_id


# ============================================================
# DSA PART 2: Searching (linear search with filters)
# ============================================================
def search_resources(resources, resource_type="", min_capacity=0, building="", status=""):
    """Go through every resource once and keep only those that match all filters."""
    results = []
    for resource in resources:
        if resource_type and resource["resource_type"] != resource_type:
            continue
        if resource["capacity"] < min_capacity:
            continue
        if building and resource["building"] != building:
            continue
        if status and resource["status"] != status:
            continue
        results.append(resource)
    return results


# ============================================================
# DSA PART 3: Sorting
# ============================================================
# Small "key" functions: sorted() calls them to decide the order.
def get_name(resource):
    return resource["name"].lower()


def get_capacity(resource):
    return resource["capacity"]


def get_availability_rank(resource):
    # 0 comes first, so "Available" resources are listed before the others
    return 0 if resource["status"] == "Available" else 1


def sort_resources(resources, sort_by):
    """Sort by capacity, availability or name (default). sorted() keeps equal items in order."""
    if sort_by == "capacity":
        return sorted(resources, key=get_capacity)
    if sort_by == "availability":
        return sorted(resources, key=get_availability_rank)
    return sorted(resources, key=get_name)


# ============================================================
# DSA PART 4: Queue (first come, first served)
# ============================================================
# When a booking fails because of a conflict, the request waits here.
# When a booking is cancelled, we go through the queue from the front
# and book the first request that now fits.
# Note: this queue lives in memory, so it is cleared when the server restarts.
waiting_queue = deque()
next_waiting_id = 1


def add_to_waiting_queue(resource_id, resource_name, booking_date, start_time, end_time, students, purpose):
    """Add a request to the back of the queue. Returns its position (1 = first)."""
    global next_waiting_id
    waiting_queue.append({
        "id": next_waiting_id,
        "resource_id": resource_id,
        "resource_name": resource_name,
        "date": booking_date,
        "start_time": start_time,
        "end_time": end_time,
        "student_count": students,
        "purpose": purpose,
    })
    next_waiting_id += 1
    return len(waiting_queue)


def process_waiting_queue():
    """
    Look at each waiting request once, from the front of the queue.
    If it can be booked now, book it. Otherwise it goes back to the end.
    Returns a list of messages about the requests that were booked.
    """
    messages = []
    resources_by_id = build_resource_dict(database.get_resources())
    today = date.today().isoformat()

    for _ in range(len(waiting_queue)):
        item = waiting_queue.popleft()            # take the first request

        resource = resources_by_id.get(item["resource_id"])
        if resource is None or item["date"] < today:
            continue                              # resource deleted or date passed: drop it

        is_free = database.check_availability(
            item["resource_id"], item["date"], item["start_time"], item["end_time"]
        )
        if resource["status"] == "Available" and is_free:
            database.add_booking(
                item["resource_id"], item["date"], item["start_time"],
                item["end_time"], item["student_count"], item["purpose"],
            )
            messages.append(
                f"Waiting list: {item['resource_name']} on {item['date']} "
                f"({item['start_time']}-{item['end_time']}) was booked automatically."
            )
        else:
            waiting_queue.append(item)            # still blocked: back of the queue
    return messages


# ============================================================
# Recommendation logic
# ============================================================
def has_equipment(resource, required_items):
    """True if the resource has every required item (e.g. ['projector', 'ac'])."""
    equipment_text = (resource["equipment"] or "").lower()
    for item in required_items:
        if item not in equipment_text:
            return False
    return True


def recommend_resource(resources, students, resource_type, equipment_text):
    """
    Steps (same as the project description):
      1. keep resources of the chosen type
      2. remove resources with too little capacity
      3. remove resources that are not available
      4. check equipment
      5. sort by closest suitable capacity (smallest room that still fits)
    The first item in the returned list is the best recommendation.
    """
    required_items = []
    for part in equipment_text.split(","):
        part = part.strip().lower()
        if part:
            required_items.append(part)

    suitable = []
    for resource in resources:
        if resource_type and resource["resource_type"] != resource_type:
            continue
        if resource["capacity"] < students:
            continue
        if resource["status"] != "Available":
            continue
        if not has_equipment(resource, required_items):
            continue
        suitable.append(resource)

    return sorted(suitable, key=get_capacity)


def build_reasons(resource, students, equipment_text):
    """Short explanation shown under the recommended resource."""
    reasons = [f"Capacity is sufficient ({resource['capacity']} seats for {students} students)"]
    if equipment_text.strip():
        reasons.append(f"Required equipment is available: {equipment_text.strip()}")
    reasons.append("Resource is available")
    return reasons


# ============================================================
# Booking logic
# ============================================================
def read_booking_slot(form):
    """
    Check the resource, date and times from a form.
    Returns (resource_id, date_text, start_text, end_text).
    Raises ValueError with a friendly message if something is wrong.
    """
    try:
        resource_id = int(form.get("resource_id", ""))
    except ValueError:
        raise ValueError("Please choose a resource.")

    date_text = form.get("date", "")
    start_text = form.get("start_time", "")
    end_text = form.get("end_time", "")

    try:
        booking_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        start = datetime.strptime(start_text, "%H:%M")
        end = datetime.strptime(end_text, "%H:%M")
    except ValueError:
        raise ValueError("Please enter a valid date, start time and end time.")

    if booking_date < date.today():
        raise ValueError("You cannot book a date in the past.")
    if end <= start:
        raise ValueError("End time must be after the start time.")

    return resource_id, date_text, start_text, end_text


def make_booking(form):
    """
    Run the booking steps. Returns (result, message)
    where result is 'ok', 'conflict' or 'error'.
    """
    # Read and validate the form
    try:
        resource_id, booking_date, start_time, end_time = read_booking_slot(form)
    except ValueError as error:
        return "error", str(error)

    try:
        students = int(form.get("student_count", ""))
    except ValueError:
        students = 0
    if students <= 0:
        return "error", "Number of students must be a positive whole number."

    purpose = form.get("purpose", "").strip()
    if not purpose:
        return "error", "Please enter the purpose of the booking."

    # Step 1: does the resource exist? (dictionary lookup)
    resources_by_id = build_resource_dict(database.get_resources())
    resource = resources_by_id.get(resource_id)
    if resource is None:
        return "error", "Booking failed. This resource does not exist."

    # Step 1b: is the resource available (not under maintenance)?
    if resource["status"] != "Available":
        return "error", f"Booking failed. {resource['name']} is not available ({resource['status']})."

    # Step 2: is the capacity enough?
    if students > resource["capacity"]:
        return "error", (
            f"Booking failed. {resource['name']} holds only {resource['capacity']} students, "
            f"but you entered {students}."
        )

    # Step 3 + 4: is there another booking at the same time?
    if not database.check_availability(resource_id, booking_date, start_time, end_time):
        position = add_to_waiting_queue(
            resource_id, resource["name"], booking_date, start_time, end_time, students, purpose
        )
        return "conflict", (
            f"Booking failed. Booking conflict: {resource['name']} is already booked during this time. "
            f"Your request was added to the waiting list (position {position})."
        )

    # Step 5: no conflict, save the booking
    database.add_booking(resource_id, booking_date, start_time, end_time, students, purpose)
    return "ok", "Booking successful!"


# ============================================================
# Resource form helper
# ============================================================
def read_resource_form(form):
    """Validate the add/edit resource form. Returns (data_dict, error_message)."""
    name = form.get("name", "").strip()
    building = form.get("building", "").strip()
    equipment = form.get("equipment", "").strip()
    resource_type = form.get("resource_type", "")
    status = form.get("status", "Available")

    try:
        capacity = int(form.get("capacity", ""))
        floor = int(form.get("floor", ""))
    except ValueError:
        return None, "Capacity and floor must be whole numbers."

    if not name or not building:
        return None, "Name and building are required."
    if resource_type not in RESOURCE_TYPES:
        return None, "Please choose a valid resource type."
    if status not in STATUS_LIST:
        return None, "Please choose a valid status."
    if capacity <= 0:
        return None, "Capacity must be greater than 0."

    data = {
        "name": name, "resource_type": resource_type, "capacity": capacity,
        "building": building, "floor": floor, "equipment": equipment, "status": status,
    }
    return data, None


# ============================================================
# Routes (web pages)
# ============================================================
@app.errorhandler(mysql.connector.Error)
def handle_database_error(error):
    """Any MySQL problem (server off, wrong password, missing table) ends up here."""
    return (
        "<h2>Database error</h2>"
        f"<p>{escape(str(error))}</p>"
        "<p>Check that MySQL is running, that database/schema.sql was executed "
        "and that your .env file is correct.</p>"
        "<p><a href='/'>Back to home</a></p>"
    ), 500


@app.route("/")
def index():
    stats = database.get_dashboard_stats()
    return render_template("index.html", stats=stats)


# ---------------- Resources ----------------
@app.route("/resources")
def resources_page():
    all_resources = database.get_resources()

    # Read the search / sort values from the URL (?resource_type=...&min_capacity=...)
    filter_type = request.args.get("resource_type", "")
    filter_building = request.args.get("building", "")
    filter_status = request.args.get("status", "")
    sort_by = request.args.get("sort", "name")
    try:
        min_capacity = int(request.args.get("min_capacity", "") or 0)
    except ValueError:
        min_capacity = 0

    results = search_resources(all_resources, filter_type, min_capacity, filter_building, filter_status)
    results = sort_resources(results, sort_by)

    buildings = sorted({r["building"] for r in all_resources})   # a set removes duplicates

    # "Edit" button sends ?edit=<id>. Find that resource with the dictionary.
    edit_resource = None
    edit_id = request.args.get("edit", "")
    if edit_id.isdigit():
        edit_resource = build_resource_dict(all_resources).get(int(edit_id))

    return render_template(
        "resources.html",
        resources=results, total_count=len(all_resources), buildings=buildings,
        resource_types=RESOURCE_TYPES, status_list=STATUS_LIST,
        filters={"resource_type": filter_type, "min_capacity": min_capacity or "",
                 "building": filter_building, "status": filter_status, "sort": sort_by},
        edit_resource=edit_resource,
    )


@app.route("/resources/add", methods=["POST"])
def resource_add():
    data, error = read_resource_form(request.form)
    if error:
        flash(error, "error")
        return redirect(url_for("resources_page"))
    try:
        database.add_resource(data["name"], data["resource_type"], data["capacity"],
                              data["building"], data["floor"], data["equipment"], data["status"])
        flash(f"Resource {data['name']} added.", "success")
    except mysql.connector.IntegrityError:
        flash(f"A resource named {data['name']} already exists.", "error")
    return redirect(url_for("resources_page"))


@app.route("/resources/<int:resource_id>/update", methods=["POST"])
def resource_update(resource_id):
    data, error = read_resource_form(request.form)
    if error:
        flash(error, "error")
        return redirect(url_for("resources_page", edit=resource_id))
    try:
        database.update_resource(resource_id, data["name"], data["resource_type"], data["capacity"],
                                 data["building"], data["floor"], data["equipment"], data["status"])
        flash(f"Resource {data['name']} updated.", "success")
    except mysql.connector.IntegrityError:
        flash(f"A resource named {data['name']} already exists.", "error")
        return redirect(url_for("resources_page", edit=resource_id))
    return redirect(url_for("resources_page"))


@app.route("/resources/<int:resource_id>/delete", methods=["POST"])
def resource_delete(resource_id):
    database.delete_resource(resource_id)
    flash("Resource deleted.", "success")
    return redirect(url_for("resources_page"))


# ---------------- Bookings ----------------
@app.route("/bookings", methods=["GET", "POST"])
def bookings_page():
    form = request.args          # lets other pages pre-fill the form (?resource_id=3&student_count=45)

    if request.method == "POST":
        form = request.form      # keep what the user typed if the booking fails
        result, message = make_booking(request.form)
        if result == "ok":
            flash(message, "success")
            return redirect(url_for("bookings_page"))
        flash(message, "error")

    bookable = search_resources(database.get_resources(), status="Available")
    return render_template(
        "bookings.html",
        resources=sort_resources(bookable, "name"),
        bookings=database.get_bookings(),
        waiting_list=list(waiting_queue),
        form=form,
        today=date.today().isoformat(),
    )


@app.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
def booking_cancel(booking_id):
    if database.cancel_booking(booking_id):
        flash("Booking cancelled.", "success")
        # The slot is free now, so let the waiting list use it (first come, first served)
        for message in process_waiting_queue():
            flash(message, "success")
    return redirect(url_for("bookings_page"))


@app.route("/waiting/<int:waiting_id>/remove", methods=["POST"])
def waiting_remove(waiting_id):
    for item in waiting_queue:
        if item["id"] == waiting_id:
            waiting_queue.remove(item)
            break
    flash("Request removed from the waiting list.", "success")
    return redirect(url_for("bookings_page"))


@app.route("/check_availability")
def check_availability_route():
    """Called by script.js when the user clicks 'Check availability' (returns JSON)."""
    try:
        resource_id, booking_date, start_time, end_time = read_booking_slot(request.args)
    except ValueError as error:
        return jsonify({"available": False, "message": str(error)})

    resource = build_resource_dict(database.get_resources()).get(resource_id)
    if resource is None:
        return jsonify({"available": False, "message": "This resource does not exist."})
    if resource["status"] != "Available":
        return jsonify({"available": False, "message": f"{resource['name']} is under {resource['status']}."})

    if database.check_availability(resource_id, booking_date, start_time, end_time):
        return jsonify({"available": True, "message": f"{resource['name']} is free during this time."})
    return jsonify({"available": False,
                    "message": f"Booking conflict: {resource['name']} is already booked during this time."})


# ---------------- Recommendation ----------------
@app.route("/recommendation")
def recommendation_page():
    form = request.args
    searched = "students" in request.args      # True after the form is submitted
    best = None
    others = []
    error = None

    if searched:
        try:
            students = int(form.get("students", ""))
        except ValueError:
            students = 0

        if students <= 0:
            error = "Please enter the number of students (a whole number above 0)."
        else:
            equipment_text = form.get("equipment", "")
            suitable = recommend_resource(
                database.get_resources(), students, form.get("resource_type", ""), equipment_text
            )
            if suitable:
                best = suitable[0]
                best["reasons"] = build_reasons(best, students, equipment_text)
                others = suitable[1:]

    return render_template(
        "recommendation.html",
        form=form, searched=searched, error=error, best=best, others=others,
        resource_types=RESOURCE_TYPES,
    )


if __name__ == "__main__":
    # debug=True restarts the server when you save a file. Turn it off for a real deployment.
    app.run(debug=True)
