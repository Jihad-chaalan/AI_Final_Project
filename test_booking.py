#!/usr/bin/env python3
"""Test the booking flow directly"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Agent.multi_agent import book_appointment, book_appointment_slot
from Schema.Data import APPOINTMENTS

# Test 1: Call the tool directly
print("=" * 60)
print("TEST 1: Direct tool call")
print("=" * 60)
result = book_appointment_slot.invoke({
    "professional_name": 'Ali',
    "client_name": 'Malik',
    "day_of_week": 'Monday',
    "start_time": '09:00',
    "week_number": 2
})
print(f"Result: {result}")
print()

# Test 2: Call through the node
print("=" * 60)
print("TEST 2: Through the node (simulating state)")
print("=" * 60)
state = {
    "professional_name": "Ali",
    "client_name": "Malik",
    "day_of_week": "Monday",
    "start_time": "09:00",
    "week_number": 2,
    "query": "I have chest pain"
}

node_result = book_appointment(state)
print(f"Node result: {node_result}")
print()

# Show appointments
print("=" * 60)
print("CURRENT APPOINTMENTS")
print("=" * 60)
for apt in APPOINTMENTS:
    if apt["professional_id"] == 1:  # Ali's appointments
        print(f"Ali - Date: {apt['date']}, Time: {apt['start_time']}-{apt['end_time']}")



