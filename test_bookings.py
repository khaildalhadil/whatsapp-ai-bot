"""
Quick check for the bookings database, using a temporary database (your real one is not touched).
Run it with:  python test_bookings.py
"""
import os
import tempfile
from datetime import timedelta

import bookings

bookings.DB_FILE = os.path.join(tempfile.mkdtemp(), "bookings.db")
bookings.create_table()
bookings.add_sample_bookings()

tomorrow = (bookings.now().date() + timedelta(days=1)).isoformat()
yesterday = (bookings.now().date() - timedelta(days=1)).isoformat()

# 0. Times are written the 12-hour way.
assert bookings.time_label(23) == "11 مساءً" and bookings.time_label(16) == "4 مساءً"
assert bookings.time_label(0) == "12 صباحًا" and bookings.time_label(9) == "9 صباحًا"

# 1. Sample data: tomorrow has 2 bookings (5 and 8 PM), the other hours are free.
day = bookings.check_day(tomorrow)
assert day["booked_hours"] == ["5 مساءً", "8 مساءً"]
assert "6 مساءً" in day["free_hours"] and "8 مساءً" not in day["free_hours"]

# 2. Booking a free hour works and shows up.
assert bookings.book_slot(tomorrow, 18, "Khalid", "96890000000")["ok"]
assert "6 مساءً" in bookings.check_day(tomorrow)["booked_hours"]

# 3. The same hour can't be booked twice (the database's UNIQUE rule).
assert not bookings.book_slot(tomorrow, 18, "Someone else", "96890000001")["ok"]

# 4. Outside opening hours, or in the past -> refused.
assert not bookings.book_slot(tomorrow, 10, "Khalid", "96890000000")["ok"]
assert not bookings.book_slot(yesterday, 20, "Khalid", "96890000000")["ok"]

# 5. check_day never reveals other customers' names or numbers.
assert "Khalid" not in str(bookings.check_day(tomorrow))

# 6. Phone numbers are saved as 8-digit Omani numbers, whatever way the customer writes them.
for written in ["+968 9123 4567", "0096891234567", "96891234567", "٩١٢٣٤٥٦٧", "9123 4567"]:
    assert bookings.local_number(written) == "91234567", written
bookings.book_slot(tomorrow, 19, "Khalid", "+968 9123 4567")
assert any(b["hour"] == 19 and b["phone"] == "91234567" for b in bookings.upcoming())

# 7. upcoming() lists this week's bookings in date and time order.
week = bookings.upcoming()
assert week == sorted(week, key=lambda b: (b["date"], b["hour"]))

print("All booking checks passed")
