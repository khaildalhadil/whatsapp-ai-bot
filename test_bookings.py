"""
Quick check for the bookings table, using a temporary Excel file (your real one is not touched).
Run it with:  python test_bookings.py
"""
import os
import tempfile
from datetime import timedelta

import bookings

bookings.FILE = os.path.join(tempfile.mkdtemp(), "bookings.xlsx")
bookings.create_sample_file()

tomorrow = (bookings.now().date() + timedelta(days=1)).isoformat()
yesterday = (bookings.now().date() - timedelta(days=1)).isoformat()

# 1. Sample data: tomorrow has 2 bookings (17:00 and 20:00), the other hours are free.
day = bookings.check_day(tomorrow)
assert day["booked_hours"] == ["17:00", "20:00"]
assert "18:00" in day["free_hours"] and "20:00" not in day["free_hours"]

# 2. Booking a free hour works and shows up in the table.
assert bookings.book_slot(tomorrow, 18, "Khalid", "96890000000")["ok"]
assert "18:00" in bookings.check_day(tomorrow)["booked_hours"]

# 3. The same hour can't be booked twice.
assert not bookings.book_slot(tomorrow, 18, "Someone else", "96890000001")["ok"]

# 4. Outside opening hours, or in the past -> refused.
assert not bookings.book_slot(tomorrow, 10, "Khalid", "96890000000")["ok"]
assert not bookings.book_slot(yesterday, 20, "Khalid", "96890000000")["ok"]

# 5. check_day never reveals other customers' names or numbers.
assert "Khalid" not in str(bookings.check_day(tomorrow))

print("All booking checks passed")
