# Dashboard/dashboard.py

import streamlit as st
import sys
import os
from datetime import datetime, timedelta
from collections import Counter
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Schema.Data import Doctors, APPOINTMENTS, CLIENTS, Doctors_TIMESLOTS, MEDICAL_RECORDS
from RAG.RAG_steps.vector_db import get_db_collection

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

st.title("📊 Medical System Dashboard")
st.caption("Real-time analytics and insights")

# Get current date for filtering
today = datetime.now().date()

# ============================================================
# TOP METRICS ROW
# ============================================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "👨‍⚕️ Total Doctors",
        len(Doctors),
        help="Active doctors in system"
    )

with col2:
    st.metric(
        "📅 Total Appointments",
        len(APPOINTMENTS),
        help="All time bookings"
    )

with col3:
    total_revenue = sum(
        next((d['Fee'] for d in Doctors if d['id'] == apt['professional_id']), 0)
        for apt in APPOINTMENTS
    )
    st.metric(
        "💰 Total Revenue",
        f"${total_revenue}",
        help="Sum of all appointment fees"
    )

with col4:
    st.metric(
        "👥 Registered Clients",
        len(CLIENTS),
        help="Total clients in system"
    )

st.divider()

# ============================================================
# SECOND ROW - CHARTS
# ============================================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Appointments by Doctor")
    
    # Count appointments per doctor
    doctor_counts = Counter(apt['professional_id'] for apt in APPOINTMENTS)
    doctor_data = []
    for doc in Doctors:
        count = doctor_counts.get(doc['id'], 0)
        doctor_data.append({
            'Doctor': doc['name'],
            'Appointments': count
        })
    
    df_doctors = pd.DataFrame(doctor_data)
    st.bar_chart(df_doctors.set_index('Doctor'))

with col2:
    st.subheader("🥧 Appointments by Specialty")
    
    # Count by specialty
    specialty_counts = Counter()
    for apt in APPOINTMENTS:
        doctor = next((d for d in Doctors if d['id'] == apt['professional_id']), None)
        if doctor:
            specialty_counts[doctor['specialty']] += 1
    
    if specialty_counts:
        df_specialty = pd.DataFrame(
            list(specialty_counts.items()),
            columns=['Specialty', 'Count']
        )
        st.bar_chart(df_specialty.set_index('Specialty'))

st.divider()

# ============================================================
# THIRD ROW - REVENUE & TRENDS
# ============================================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("💵 Revenue by Doctor")
    
    revenue_data = []
    for doc in Doctors:
        doc_appointments = [apt for apt in APPOINTMENTS if apt['professional_id'] == doc['id']]
        revenue = len(doc_appointments) * doc['Fee']
        revenue_data.append({
            'Doctor': doc['name'],
            'Revenue': revenue,
            'Bookings': len(doc_appointments)
        })
    
    df_revenue = pd.DataFrame(revenue_data)
    st.dataframe(df_revenue, use_container_width=True)


st.divider()

# ============================================================
# FOURTH ROW - TABLES
# ============================================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("📅 Upcoming Appointments")
    
    upcoming = []
    for apt in APPOINTMENTS:
        try:
            apt_date = datetime.strptime(apt['date'], "%Y-%m-%d").date()
            if apt_date >= today:
                doctor = next((d for d in Doctors if d['id'] == apt['professional_id']), None)
                client = next((c for c in CLIENTS if c['id'] == apt['client_id']), None)
                if doctor and client:
                    upcoming.append({
                        'Date': apt['date'],
                        'Doctor': doctor['name'],
                        'Client': client['name'],
                        'Time': f"{apt['start_time']}-{apt['end_time']}"
                    })
        except:
            pass
    
    if upcoming:
        df_upcoming = pd.DataFrame(sorted(upcoming, key=lambda x: x['Date']))
        st.dataframe(df_upcoming, use_container_width=True)
    else:
        st.info("No upcoming appointments")

with col2:
    st.subheader("👥 Most Active Clients")
    
    client_counts = Counter(apt['client_id'] for apt in APPOINTMENTS)
    active_clients = []
    for client_id, count in client_counts.most_common(5):
        client = next((c for c in CLIENTS if c['id'] == client_id), None)
        if client:
            active_clients.append({
                'Client': client['name'],
                'Bookings': count
            })
    
    if active_clients:
        df_clients = pd.DataFrame(active_clients)
        st.dataframe(df_clients, use_container_width=True)

st.divider()

# ============================================================
# FIFTH ROW - RAG SYSTEM STATS
# ============================================================
st.subheader("📚 RAG Document System")

col1, col2, col3 = st.columns(3)

try:
    collection = get_db_collection()
    doc_count = collection.count()
    
    with col1:
        st.metric("📄 Document Chunks", doc_count)
    
    with col2:
        st.metric("🗄️ Collection", "Active")
    
    with col3:
        st.metric("💾 Database", "ChromaDB")
except:
    st.warning("⚠️ RAG system not initialized. Upload documents in the Load page.")

st.divider()

# ============================================================
# ADDITIONAL INSIGHTS
# ============================================================
st.subheader("💡 Key Insights")

col1, col2, col3 = st.columns(3)

with col1:
    # Most popular time
    time_counts = Counter(apt['start_time'] for apt in APPOINTMENTS)
    if time_counts:
        popular_time = time_counts.most_common(1)[0]
        st.info(f"🕐 **Most Popular Time:** {popular_time[0]} ({popular_time[1]} bookings)")

with col2:
    # Most expensive doctor bookings
    revenue_by_doctor = {}
    for apt in APPOINTMENTS:
        doctor = next((d for d in Doctors if d['id'] == apt['professional_id']), None)
        if doctor:
            revenue_by_doctor[doctor['name']] = revenue_by_doctor.get(doctor['name'], 0) + doctor['Fee']
    
    if revenue_by_doctor:
        top_earner = max(revenue_by_doctor.items(), key=lambda x: x[1])
        st.success(f"🏆 **Top Earner:** Dr. {top_earner[0]} (${top_earner[1]})")

with col3:
    # Average appointments per client
    avg_bookings = len(APPOINTMENTS) / len(CLIENTS) if CLIENTS else 0
    st.info(f"📊 **Avg Bookings/Client:** {avg_bookings:.1f}")