"""
The pitch bookings, kept in a small SQLite database (bookings.db).

SQLite comes with Python: the whole database is one file, no server to install.
Each row of the "bookings" table is one booked hour: date, hour, name, phone.

The AI uses check_day() and book_slot() to answer customers on WhatsApp,
and the /dashboard page uses upcoming() to show the bookings.

Run "python bookings.py" to reset the database to sample bookings.
"""
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

# Where the database file lives. On Azure we point this to a folder that survives redeploys.
DB_FILE = os.getenv("DATABASE_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "bookings.db")

# Arabic day names, in Python's order: weekday() is 0 for Monday ... 6 for Sunday.
ARABIC_DAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]

OPEN_HOUR = 16   # the pitch opens at 4 PM ...
CLOSE_HOUR = 24  # ... and closes at midnight, so the last booking starts at 11 PM (23)

# Oman time (UTC+4, no daylight saving). Azure servers run on UTC, so we set it ourselves.
LOCAL_TIME = timezone(timedelta(hours=4))


def run(sql, params=()):
    """Run one SQL statement on the database and return the rows as a list of dicts."""
    with closing(sqlite3.connect(DB_FILE)) as db:
        db.row_factory = sqlite3.Row  # lets us read columns by name: row["date"]
        rows = db.execute(sql, params).fetchall()
        db.commit()
        return [dict(row) for row in rows]


def create_table():
    # UNIQUE (date, hour) makes the database itself refuse a second booking of the same hour,
    # even if two customers press "book" at the same moment.
    run("""
        CREATE TABLE IF NOT EXISTS bookings (
            id         INTEGER PRIMARY KEY,
            date       TEXT    NOT NULL,              -- "2026-10-23"
            hour       INTEGER NOT NULL,              -- 24h start hour, e.g. 23 for 11 PM
            name       TEXT    NOT NULL,
            phone      TEXT    NOT NULL,              -- 8-digit Omani number, e.g. "91234567"
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE (date, hour)
        )
    """)


def now():
    """The current date and time in Oman."""
    return datetime.now(LOCAL_TIME).replace(tzinfo=None)


def local_number(phone):
    """Keep the 8-digit Omani number only: "+968 9123 4567" or "٩١٢٣٤٥٦٧" -> "91234567"."""
    # int(c) also turns Arabic digits like "٩" into 9.
    digits = "".join(str(int(c)) for c in str(phone) if c.isdecimal())
    digits = digits.removeprefix("00")  # 00968... -> 968...
    if len(digits) == 11 and digits.startswith("968"):
        digits = digits[3:]
    return digits


def time_label(hour):
    """Turn a 24h hour into the 12h Arabic way people say it: 23 -> "11 مساءً", 9 -> "9 صباحًا"."""
    suffix = "صباحًا" if hour < 12 else "مساءً"
    return f"{hour % 12 or 12} {suffix}"


def booked_hours(day):
    """The booked hours (24h numbers, e.g. [17, 20]) of one date."""
    rows = run("SELECT hour FROM bookings WHERE date = ? ORDER BY hour", (day.isoformat(),))
    return [row["hour"] for row in rows]


def check_day(date):
    """Return the booked and free hours of one date ("YYYY-MM-DD"), written like "8 مساءً".

    Other customers' names and phone numbers are NOT returned, only the hours.
    """
    day = datetime.strptime(date, "%Y-%m-%d").date()
    booked = booked_hours(day)
    free = [h for h in range(OPEN_HOUR, CLOSE_HOUR) if h not in booked]
    return {
        "date": day.isoformat(),
        "day": day.strftime("%A"),
        "booked_hours": [time_label(h) for h in booked],
        "free_hours": [time_label(h) for h in free],
    }


def book_slot(date, hour, name, phone):
    """Book one hour for a customer. Returns {"ok": True, ...} or {"ok": False, "reason": ...}."""
    day = datetime.strptime(date, "%Y-%m-%d").date()

    if not OPEN_HOUR <= hour < CLOSE_HOUR:
        return {"ok": False, "reason": f"The pitch is open from {time_label(OPEN_HOUR)} to midnight."}
    if datetime(day.year, day.month, day.day, hour) < now():
        return {"ok": False, "reason": "This time is already in the past."}

    try:
        run("INSERT INTO bookings (date, hour, name, phone) VALUES (?, ?, ?, ?)",
            (day.isoformat(), hour, name, local_number(phone)))
    except sqlite3.IntegrityError:  # the UNIQUE (date, hour) rule said no
        return {"ok": False, "reason": "This hour is already booked."}

    return {"ok": True, "date": day.isoformat(), "day": day.strftime("%A"), "time": time_label(hour), "name": name}


def upcoming(days=7):
    """All bookings from today for the next `days` days, oldest first (for the dashboard)."""
    today = now().date()
    last_day = today + timedelta(days=days - 1)
    return run(
        "SELECT * FROM bookings WHERE date BETWEEN ? AND ? ORDER BY date, hour",
        (today.isoformat(), last_day.isoformat()),
    )


def add_sample_bookings():
    """Delete every booking and add made-up ones for the next 7 days (1 to 3 per day)."""
    run("DELETE FROM bookings")
    names = ["أحمد", "محمد", "سالم", "يوسف", "علي", "سعيد", "حمد"]
    for d in range(7):
        day = now().date() + timedelta(days=d)
        for i, hour in enumerate([17, 20, 22][: d % 3 + 1]):
            fake_phone = f"9{d}{i}12345"  # made-up 8-digit Omani number
            run("INSERT INTO bookings (date, hour, name, phone) VALUES (?, ?, ?, ?)",
                (day.isoformat(), hour, names[(d + i) % 7], fake_phone))


# The first time the bot runs, create the database with sample bookings.
if not os.path.exists(DB_FILE):
    create_table()
    add_sample_bookings()


if __name__ == "__main__":
    create_table()
    add_sample_bookings()
    print(f"Reset {DB_FILE} to sample bookings:")
    for booking in upcoming():
        print(booking["date"], time_label(booking["hour"]), booking["name"], booking["phone"])
