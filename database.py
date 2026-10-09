"""
database.py
-----------
All MySQL code lives in this file. app.py calls these functions
and never writes SQL itself, so it is easy to find and change a query.
"""

import os

import mysql.connector
from dotenv import load_dotenv

# Read the .env file (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME).
# The password is never written in the code.
load_dotenv()


# ------------------------------------------------------------
# Connection and two small helpers
# ------------------------------------------------------------
def get_connection():
    """Open a new connection to MySQL using the values from .env"""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "campus_optimizer"),
    )


def run_query(sql, params=None):
    """Run a SELECT query and return the rows as a list of dictionaries."""
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        connection.close()


def run_command(sql, params=None):
    """Run an INSERT / UPDATE / DELETE and return how many rows changed."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params or ())
        connection.commit()
        changed_rows = cursor.rowcount
        cursor.close()
        return changed_rows
    finally:
        connection.close()


# ------------------------------------------------------------
# Resources
# ------------------------------------------------------------
def get_resources():
    """Return every resource, ordered by name."""
    return run_query("SELECT * FROM resources ORDER BY name")


def add_resource(name, resource_type, capacity, building, floor, equipment, status):
    sql = """
        INSERT INTO resources (name, resource_type, capacity, building, floor, equipment, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    return run_command(sql, (name, resource_type, capacity, building, floor, equipment, status))


def update_resource(resource_id, name, resource_type, capacity, building, floor, equipment, status):
    sql = """
        UPDATE resources
        SET name = %s, resource_type = %s, capacity = %s, building = %s,
            floor = %s, equipment = %s, status = %s
        WHERE resource_id = %s
    """
    return run_command(sql, (name, resource_type, capacity, building, floor, equipment, status, resource_id))


def delete_resource(resource_id):
    # The foreign key (ON DELETE CASCADE) also removes this resource's bookings.
    return run_command("DELETE FROM resources WHERE resource_id = %s", (resource_id,))


# ------------------------------------------------------------
# Bookings
# ------------------------------------------------------------
def get_bookings():
    """Return all bookings with the resource name, newest dates first."""
    sql = """
        SELECT b.booking_id, b.resource_id, r.name AS resource_name,
               b.date, b.student_count, b.purpose, b.status,
               LEFT(CAST(b.start_time AS CHAR), 5) AS start_display,
               LEFT(CAST(b.end_time AS CHAR), 5)   AS end_display
        FROM bookings b
        JOIN resources r ON b.resource_id = r.resource_id
        ORDER BY b.date DESC, b.start_time
    """
    return run_query(sql)


def add_booking(resource_id, booking_date, start_time, end_time, student_count, purpose):
    sql = """
        INSERT INTO bookings (resource_id, date, start_time, end_time, student_count, purpose, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'Confirmed')
    """
    return run_command(sql, (resource_id, booking_date, start_time, end_time, student_count, purpose))


def cancel_booking(booking_id):
    """Mark a booking as Cancelled (only if it is still Confirmed). Returns rows changed."""
    sql = "UPDATE bookings SET status = 'Cancelled' WHERE booking_id = %s AND status = 'Confirmed'"
    return run_command(sql, (booking_id,))


def check_availability(resource_id, booking_date, start_time, end_time):
    """
    Return True if the resource is FREE during the requested time.

    Two time ranges overlap when:
        existing_start < new_end   AND   existing_end > new_start
    Example: existing 10:00-11:00, new 10:30-11:30
        10:00 < 11:30 (true) AND 11:00 > 10:30 (true)  ->  overlap = conflict.
    A booking that starts exactly when another ends (11:00) is NOT a conflict.
    Cancelled bookings are ignored.
    """
    sql = """
        SELECT COUNT(*) AS conflicts
        FROM bookings
        WHERE resource_id = %s
          AND date = %s
          AND status = 'Confirmed'
          AND start_time < %s
          AND end_time > %s
    """
    rows = run_query(sql, (resource_id, booking_date, end_time, start_time))
    return rows[0]["conflicts"] == 0


# ------------------------------------------------------------
# Dashboard numbers (always read from MySQL, never hardcoded)
# ------------------------------------------------------------
def get_dashboard_stats():
    total = run_query("SELECT COUNT(*) AS n FROM resources")[0]["n"]
    available = run_query("SELECT COUNT(*) AS n FROM resources WHERE status = 'Available'")[0]["n"]
    booked_today = run_query(
        "SELECT COUNT(DISTINCT resource_id) AS n FROM bookings "
        "WHERE date = CURDATE() AND status = 'Confirmed'"
    )[0]["n"]
    total_bookings = run_query("SELECT COUNT(*) AS n FROM bookings WHERE status = 'Confirmed'")[0]["n"]

    return {
        "total_resources": total,
        "available_resources": available,
        "booked_resources": booked_today,
        "total_bookings": total_bookings,
    }
