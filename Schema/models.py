from typing import TypedDict


class Professional(TypedDict):
    id: int
    name: str
    Phone: str
    email: str
    Fee: int
    location: str
class TimeSlot(TypedDict):
    id: int
    professional_id: int
    start_time: str
    end_time: str
    dayofweek: str
    available: bool
class Client(TypedDict):
    id: int
    name: str
    Phone: str
    email: str
    Age: int
class Appointment(TypedDict):
    id: int
    professional_id: int
    client_id: int
    start_time: str
    end_time: str
    duration: int
    date: str
    