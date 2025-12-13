from Schema.models import Doctors, TimeSlot, Appointment, Client, MedicalRecord

Doctors=[
    Doctors(id=1, name="Ali", Phone="01123456789", email="", Fee=100, location="Beirut",specialty="Cardiology"),
    Doctors(id=2, name="Malik", Phone="01123456789", email="", Fee=50, location="Beirut",specialty="Dermatology"),
    Doctors(id=3, name="Fatima", Phone="01123456789", email="", Fee=70, location="Byblos",specialty="Pediatrics"),
    Doctors(id=4, name="Sara", Phone="01123456789", email="", Fee=120, location="Saida",specialty="Neurology"),
    Doctors(id=5, name="Mohamed", Phone="01123456789", email="", Fee=90, location="Tyre",specialty="Cardiology"),
]
Doctors_TIMESLOTS=[
    TimeSlot(id=1, professional_id=1, start_time="09:00", end_time="10:00", dayofweek="Monday", available=True),
    TimeSlot(id=2, professional_id=1, start_time="10:00", end_time="11:00", dayofweek="Monday", available=True),
    TimeSlot(id=3, professional_id=2, start_time="10:00", end_time="11:00", dayofweek="Tuesday", available=True),
    TimeSlot(id=4, professional_id=3, start_time="10:00", end_time="11:00", dayofweek="Monday", available=True),
    TimeSlot(id=5, professional_id=4, start_time="10:00", end_time="11:00", dayofweek="Wednesday", available=True),
    TimeSlot(id=6, professional_id=5, start_time="10:00", end_time="11:00", dayofweek="Tuesday", available=True),
    TimeSlot(id=7, professional_id=1, start_time="11:00", end_time="12:00", dayofweek="Thursday", available=True),
    TimeSlot(id=8, professional_id=2, start_time="11:00", end_time="12:00", dayofweek="Wednesday", available=True),
    TimeSlot(id=9, professional_id=3, start_time="11:00", end_time="12:00", dayofweek="Monday", available=True),
    TimeSlot(id=10, professional_id=4, start_time="11:00", end_time="12:00", dayofweek="Thursday", available=True),
]
APPOINTMENTS=[
    Appointment(id=1, professional_id=1, client_id=1, start_time="10:00", end_time="11:00", duration=60, date="2025-12-15"),
    Appointment(id=2, professional_id=2, client_id=2, start_time="10:00", end_time="11:00", duration=60, date="2025-12-22"),
    Appointment(id=3, professional_id=3, client_id=3, start_time="10:00", end_time="11:00", duration=60, date="2025-12-01"),
    Appointment(id=4, professional_id=4, client_id=4, start_time="10:00", end_time="11:00", duration=60, date="2025-12-03"),
    Appointment(id=5, professional_id=4, client_id=4, start_time="11:00", end_time="12:00", duration=60, date="2025-12-04"),
    Appointment(id=6, professional_id=1, client_id=2, start_time="11:00", end_time="12:00", duration=60, date="2025-12-18"),
    Appointment(id=7, professional_id=2, client_id=2, start_time="10:00", end_time="11:00", duration=60, date="2026-1-27"),
]
CLIENTS=[
    Client(id=1, name="Ali", Phone="01123456789", email="", Age=25),
    Client(id=2, name="Malik", Phone="01123456789", email="", Age=26),
    Client(id=3, name="Fatima", Phone="01123456789", email="", Age=27),
    Client(id=4, name="Sara", Phone="01123456789", email="", Age=28),
]
MEDICAL_RECORDS=[
    MedicalRecord(id=1, client_id=1,professional_id=1,symptoms="", diagnosis="", treatment="",date="2025-12-01" ),
    MedicalRecord(id=2, client_id=2,professional_id=2,symptoms="", diagnosis="", treatment="",date="2025-12-02" ),
    MedicalRecord(id=3, client_id=3,professional_id=3,symptoms="", diagnosis="", treatment="",date="2025-12-01" ),
    MedicalRecord(id=4, client_id=4, professional_id=4, symptoms="", diagnosis="", treatment="", date="2025-12-03" ),
    MedicalRecord(id=5, client_id=4, professional_id=5, symptoms="", diagnosis="", treatment="", date="2025-12-04" ),

]