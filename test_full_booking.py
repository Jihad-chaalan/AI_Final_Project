#!/usr/bin/env python3
"""Complete end-to-end test with fresh data"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and reset data
from Schema import Data
from Schema.models import Appointment, Client

# Save original appointments count
original_count = len(Data.APPOINTMENTS)

print("=" * 70)
print("END-TO-END BOOKING TEST")
print("=" * 70)
print(f"\nStarting with {original_count} appointments in the system")
print(f"Ali (professional_id=1) has {len([a for a in Data.APPOINTMENTS if a['professional_id'] == 1])} booked appointments\n")

# Now import the agent components
from Agent.multi_agent import book_appointment

# Test booking through the node
print("-" * 70)
print("Booking: Malik with Ali on Monday at 09:00 for week 2")
print("-" * 70)

state = {
    "professional_name": "Ali",
    "client_name": "Malik",
    "day_of_week": "Monday",
    "start_time": "09:00",
    "week_number": 2,
    "query": "I have chest pain"
}

result = book_appointment(state)
print(f"\n✓ Result: {result['message']}\n")

# Verify the appointment was added
new_count = len(Data.APPOINTMENTS)
print(f"Appointments after booking: {new_count}")
print(f"New appointments added: {new_count - original_count}")

# Show Ali's appointments
print(f"\nAli's appointments:")
for apt in Data.APPOINTMENTS:
    if apt["professional_id"] == 1:
        print(f"  - Date: {apt['date']}, Time: {apt['start_time']}-{apt['end_time']}, Client ID: {apt['client_id']}")

# Test duplicate booking (should fail)
print("\n" + "-" * 70)
print("Attempting duplicate booking (should fail)...")
print("-" * 70)

result2 = book_appointment(state)
print(f"\n✓ Result: {result2['message']}\n")

print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)

