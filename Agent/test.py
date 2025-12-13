# Agent/test.py - Complete Multi-Agent Booking System

import streamlit as st
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Agent.multi_agent import app, Doctors, CLIENTS, APPOINTMENTS

# Page config
st.set_page_config(page_title="AI Booking Agent", page_icon="🏥", layout="centered")

# Initialize session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"chat_{int(datetime.now().timestamp())}"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "client_name" not in st.session_state:
    st.session_state.client_name = None
if "waiting_for" not in st.session_state:
    st.session_state.waiting_for = "name"
if "current_state" not in st.session_state:
    st.session_state.current_state = None

def get_thread_config():
    return {"configurable": {"thread_id": st.session_state.thread_id}, "recursion_limit": 25}

def add_message(role, content):
    st.session_state.messages.append({"role": role, "content": content})

# Header
st.title("🏥 AI Medical Appointment Booking")
st.caption("Multi-Agent System with LangGraph")

# Sidebar
with st.sidebar:
    st.header("📊 System Info")
    
    with st.expander("🩺 Available Doctors", expanded=True):
        for doc in Doctors:
            st.write(f"**{doc['name']}**")
            st.caption(f"{doc['specialty']}")
            st.caption(f"{doc['location']} | ${doc['Fee']}")
            st.divider()
    
    with st.expander("👥 Clients"):
        for client in CLIENTS:
            st.write(f"• {client['name']}")
    
    with st.expander("📅 Recent Bookings"):
        st.metric("Total", len(APPOINTMENTS))
        if APPOINTMENTS:
            for apt in APPOINTMENTS[-3:]:
                doctor = next((d for d in Doctors if d['id'] == apt['professional_id']), None)
                if doctor:
                    st.caption(f"✓ {doctor['name']} - {apt['date']}")
    
    st.divider()
    st.write("**Current Status:**")
    st.code(f"Stage: {st.session_state.waiting_for}")
    if st.session_state.client_name:
        st.code(f"Client: {st.session_state.client_name}")
    st.code(f"Thread: ...{st.session_state.thread_id[-8:]}")
    
    if st.session_state.current_state:
        with st.expander("🔍 Debug State"):
            state = st.session_state.current_state
            st.json({
                "classification": state.get('classification'),
                "professional_name": state.get('professional_name'),
                "specialty": state.get('specialty'),
                "has_timeslots": bool(state.get('timeslots')),
                "user_action": state.get('user_action'),
                "week_number": state.get('week_number')
            })
    
    st.divider()
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# Chat Display
st.subheader("💬 Conversation")
chat_container = st.container(height=400, border=True)

with chat_container:
    if st.session_state.messages:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    else:
        with st.chat_message("assistant"):
            st.markdown("👋 **Welcome!** I'll help you book a medical appointment.\n\n**First, what's your name?**")

# Chat Input
user_input = st.chat_input("Type your message here...")

if user_input:
    add_message("user", user_input)
    
    try:
        # ============================================================
        # STAGE 1: GET CLIENT NAME
        # ============================================================
        if st.session_state.waiting_for == "name":
            st.session_state.client_name = user_input
            st.session_state.waiting_for = "query"
            
            response = f"Nice to meet you, **{user_input}**! 👋\n\n"
            response += "How can I help you today?\n\n"
            response += "**You can:**\n"
            response += "• Describe symptoms: *'I have chest pain'*\n"
            response += "• Request a doctor: *'Book with Dr. Ali'*\n"
            response += "• Search specialists: *'Show cardiologists in Beirut'*"
            
            add_message("assistant", response)
        
        # ============================================================
        # STAGE 2: PROCESS INITIAL QUERY
        # ============================================================
        elif st.session_state.waiting_for == "query":
            with st.spinner("🤖 Analyzing your request..."):
                # INVOKE 1: Start workflow with query
                app.invoke({
                    "query": user_input,
                    "client_name": st.session_state.client_name
                }, get_thread_config())
                
                # INVOKE 2: Continue classification
                app.invoke(None, get_thread_config())
                
                # Get state
                state = app.get_state(get_thread_config()).values
                st.session_state.current_state = state
                
                # Check which path we took
                if state.get('classification') == "professional_not_exists":
                    # SYMPTOM-BASED PATH
                    specialty = state.get('specialty', 'a specialist')
                    prof_list = state.get('professional_list', '')
                    
                    response = f"**Identified Specialty:** {specialty}\n\n"
                    response += f"**Available Specialists:**\n{prof_list}\n\n"
                    response += "**Which doctor would you like?** (Type the name)"
                    
                    st.session_state.waiting_for = "professional"
                    add_message("assistant", response)
                    
                elif state.get('timeslots'):
                    # DIRECT PATH: Already got timeslots
                    doctor_name = state.get('professional_name', 'the doctor')
                    timeslots = state['timeslots']
                    
                    response = f"**Available slots for Dr. {doctor_name}:**\n\n```\n{timeslots}\n```\n\n"
                    response += "**To book, type:** `Day Time Week` (e.g., `Monday 09:00 2`)\n"
                    response += "**To view another week, type:** `week 5` or just `5`"
                    
                    st.session_state.waiting_for = "booking"
                    add_message("assistant", response)
                else:
                    response = "I couldn't understand that. Could you rephrase?"
                    add_message("assistant", response)
        
        # ============================================================
        # STAGE 3: SELECT PROFESSIONAL (after symptom-based search)
        # ============================================================
        elif st.session_state.waiting_for == "professional":
            professional_name = user_input.strip()
            
            with st.spinner(f"🔍 Getting slots for Dr. {professional_name}..."):
                # Update state with professional selection
                app.update_state(get_thread_config(), {
                    "professional_name": professional_name,
                    "professional_criteria": professional_name
                })
                
                # INVOKE 1: Resume workflow
                app.invoke(None, get_thread_config())
                
                # INVOKE 2: Continue through fetch and get slots
                app.invoke(None, get_thread_config())
                
                # Get state with timeslots
                state = app.get_state(get_thread_config()).values
                st.session_state.current_state = state
                
                if state.get('timeslots'):
                    timeslots = state['timeslots']
                    
                    response = f"**Available slots for Dr. {professional_name}:**\n\n```\n{timeslots}\n```\n\n"
                    response += "**To book, type:** `Day Time Week` (e.g., `Monday 09:00 2`)\n"
                    response += "**To view another week, type:** `week 5` or just `5`"
                    
                    st.session_state.waiting_for = "booking"
                    add_message("assistant", response)
                else:
                    response = f"❌ No slots available for Dr. {professional_name}.\n\n"
                    response += "Try another doctor from the list."
                    add_message("assistant", response)
                    st.session_state.waiting_for = "professional"
        
        # ============================================================
        # STAGE 4: BOOK APPOINTMENT OR VIEW DIFFERENT WEEK
        # ============================================================
        elif st.session_state.waiting_for == "booking":
            user_input_lower = user_input.strip().lower()
            
            # Check if user wants to view a different week (single digit or "week X")
            if user_input_lower.startswith("week ") or (user_input_lower.isdigit() and len(user_input.split()) == 1):
                # Extract week number
                if user_input_lower.startswith("week "):
                    week_str = user_input_lower.replace("week ", "").strip()
                else:
                    week_str = user_input_lower
                
                try:
                    week_number = int(week_str)
                    
                    if week_number < 1:
                        response = "❌ Week number must be 1 or greater."
                        add_message("assistant", response)
                    else:
                        with st.spinner(f"🔍 Getting slots for week {week_number}..."):
                            # Update state to view specific week
                            app.update_state(get_thread_config(), {
                                "user_action": "continue",
                                "week_number": week_number
                            })
                            
                            # INVOKE: Get specific week slots
                            app.invoke(None, get_thread_config())
                            
                            # Get updated state
                            state = app.get_state(get_thread_config()).values
                            st.session_state.current_state = state
                            
                            if state.get('timeslots'):
                                timeslots = state['timeslots']
                                professional_name = state.get('professional_name', 'the doctor')
                                
                                response = f"**Available slots for Dr. {professional_name} (Week {week_number}):**\n\n```\n{timeslots}\n```\n\n"
                                response += "**To book, type:** `Day Time Week` (e.g., `Wednesday 10:00 3`)\n"
                                response += "**To view another week, type:** `week 6` or just `6`"
                                
                                add_message("assistant", response)
                            else:
                                response = f"❌ No slots available for week {week_number}.\n\nTry another week or book from available slots."
                                add_message("assistant", response)
                
                except ValueError:
                    response = "❌ Invalid week number.\n\n**To view a week:** Type `week 5` or just `5`\n**To book:** Type `Day Time Week` (e.g., `Wednesday 10:00 3`)"
                    add_message("assistant", response)
            
            else:
                # Parse booking: "Wednesday 10:00 3"
                parts = user_input.strip().split()
                
                if len(parts) >= 3:
                    day_of_week = parts[0]
                    start_time = parts[1]
                    
                    # Normalize time format: if user types "10" convert to "10:00"
                    if ":" not in start_time:
                        start_time = f"{start_time}:00"
                    
                    try:
                        week_number = int(parts[2])
                        
                        if week_number < 1:
                            response = "❌ Week number must be 1 or greater.\n\n**Example:** `Wednesday 10:00 3`"
                            add_message("assistant", response)
                        else:
                            with st.spinner("📝 Booking your appointment..."):
                                # Update state with booking details
                                app.update_state(get_thread_config(), {
                                    "user_action": "book",
                                    "day_of_week": day_of_week,
                                    "start_time": start_time,
                                    "week_number": week_number
                                })
                                
                                # INVOKE: Complete booking
                                app.invoke(None, get_thread_config())
                                
                                # Get final state with fresh booking result
                                state = app.get_state(get_thread_config()).values
                                st.session_state.current_state = state
                                
                                booking_msg = state.get('message', 'Booking completed!')
                                final_answer = state.get('final_answer', '')
                                
                                if "successfully" in booking_msg.lower():
                                    response = f"✅ **Booking Successful!**\n\n{booking_msg}\n\n"
                                    if final_answer:
                                        response += f"```\n{final_answer}\n```\n\n"
                                    response += "---\n\nNeed another appointment? Just describe what you need!"
                                    
                                    st.session_state.waiting_for = "query"
                                    
                                    # START FRESH THREAD for next booking
                                    st.session_state.thread_id = f"chat_{int(datetime.now().timestamp())}"
                                    st.session_state.current_state = None
                                    
                                    st.balloons()
                                else:
                                    # Failed booking - show specific error
                                    response = f"⚠️ **Booking Failed:**\n\n{booking_msg}\n\n"
                                    response += "**Please check:**\n"
                                    response += "• Time format is HH:MM (e.g., 10:00 not 10)\n"
                                    response += "• Day is spelled correctly (Wednesday, Thursday, etc.)\n"
                                    response += "• Slot is actually available in the week you specified\n\n"
                                    response += "**Try again or type a week number to view other weeks**"
                                
                                add_message("assistant", response)
                            
                    except ValueError:
                        response = "❌ Invalid week number.\n\n**Format:** `Day Time Week`\n**Example:** `Wednesday 10:00 3`"
                        add_message("assistant", response)
                else:
                    response = "❌ Invalid format.\n\n**To book:** Type `Day Time Week` (e.g., `Wednesday 10:00 3`)\n**To view a week:** Type `week 5` or just `5`"
                    add_message("assistant", response)
    
    except Exception as e:
        error_msg = f"❌ **Error:** {str(e)}\n\nLet's start over. What would you like to do?"
        add_message("assistant", error_msg)
        st.session_state.waiting_for = "query"
        
        with st.expander("🔍 Technical Details"):
            import traceback
            st.code(traceback.format_exc())
    
    st.rerun()

# Footer
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🤖 LangGraph Multi-Agent")
with col2:
    st.caption("🧠 DeepSeek LLM")
with col3:
    st.caption(f"💾 {len(APPOINTMENTS)} bookings")