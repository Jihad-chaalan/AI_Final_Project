from langchain.agents import create_agent
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Schema.Data import Doctors, Doctors_TIMESLOTS, APPOINTMENTS, CLIENTS
from Schema.models import Appointment

load_dotenv()


# Step 1: ----------------- LLM Declaration ----------------------------
def get_gemini():
    """Returns a model to invoke Google Gemini."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    llm_model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=gemini_key,
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2
    )
    return llm_model

def get_deepseek():
    """
    returns a model to invoke DeepSeek
    """
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    url = os.getenv("DEEPSEEK_API_BASE")

    llm_model = ChatOpenAI(
        model="deepseek-chat",
        max_tokens=1000,
        timeout=30,
        api_key=deepseek_key,
        base_url=url
    )
    return llm_model
llm = get_deepseek()


# Step 2: -------------------- State Definition ---------------------
class AgentState(TypedDict):
    professional_name: str | None
    specialty: str | None
    client_name: str
    day_of_week: str | None
    start_time: str | None
    timeslots: str | None
    appointment: Appointment | None
    professional_criteria: str | None
    professional_list: str | None
    week_number: int | None
    classification: str | None
    query: str
    human_question: str | None
    message: str | None
    final_answer: str | None
    user_action: str | None  # "continue", "book", or "quit"


memory = MemorySaver()


# Step 3: --------------------- Helper Functions --------------------
def get_available_slots_for_weeks(professional_name: str, week_numbers: List[int]) -> str:
    """Get available appointments for specific weeks by comparing timeslots with booked appointments"""
    professional = next(
        (p for p in Doctors if p["name"].lower() == professional_name.lower()),
        None
    )

    if not professional:
        return f"Professional {professional_name} not found."

    prof_timeslots = [
        slot for slot in Doctors_TIMESLOTS
        if slot["professional_id"] == professional["id"]
    ]

    if not prof_timeslots:
        return f"No timeslots configured for {professional_name}."

    prof_appointments = [
        apt for apt in APPOINTMENTS
        if apt["professional_id"] == professional["id"]
    ]

    today = datetime.now()
    # Get the start of current week (Monday)
    current_week_start = today - timedelta(days=today.weekday())
    
    weeks_data = defaultdict(list)
    days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    for week_num in week_numbers:
        week_start = current_week_start + timedelta(weeks=week_num - 1)
        
        for slot in prof_timeslots:
            day_name = slot["dayofweek"].lower()
            day_index = days_of_week.index(day_name)
            
            slot_date = week_start + timedelta(days=day_index)
            
            # Skip past dates
            if slot_date.date() < today.date():
                continue
            
            # Check if this slot is already booked
            is_booked = any(
                datetime.strptime(apt["date"], "%Y-%m-%d").date() == slot_date.date()
                and apt["start_time"] == slot["start_time"]
                for apt in prof_appointments
            )
            
            if not is_booked and slot["available"]:
                weeks_data[week_num].append({
                    "date": slot_date.strftime("%Y-%m-%d"),
                    "day": slot["dayofweek"],
                    "start_time": slot["start_time"],
                    "end_time": slot["end_time"]
                })

    if not weeks_data:
        return f"No available appointments for {professional_name} in the requested weeks."
    
    result = f"Available appointments for {professional_name}:\n\n"
    
    for week_num in sorted(weeks_data.keys()):
        if weeks_data[week_num]:
            week_start = current_week_start + timedelta(weeks=week_num - 1)
            week_end = week_start + timedelta(days=6)
            week_label = "Current Week" if week_num == 1 else f"Week {week_num}" if week_num == 2 else f"Week {week_num}"
            if week_num == 2:
                week_label = "Next Week"
            result += f"{week_label} ({week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}):\n"
            
            sorted_slots = sorted(weeks_data[week_num], key=lambda x: x["date"])
            for slot in sorted_slots:
                result += f"  - {slot['day']}, {slot['date']}: {slot['start_time']} - {slot['end_time']}\n"
            result += "\n"

    return result


# Step 4: --------------------- Graph Nodes --------------------

def init_node(state: AgentState):
    return {"human_question":
                "I can help you book an appointment if you have a doctor in mind."
                "Or tell me your symptoms and I can help you find a suitable professional."}


    
def classify_question(state: AgentState):
    """Classify if the query mentions a professional name"""
    prompt = f"""
        You are a classifier for appointment booking queries.

        Available professionals in the system: {[p["name"] for p in Doctors]}.

        Task: Determine if the user's query mentions a specific professional's name from the list above.

        Question: {state['query']}

        Classify as EXACTLY ONE of these labels:
        - 'professional_exists' (if a specific professional name from the list is mentioned)
        - 'professional_not_exists' (if no professional name is mentioned or asking for help to find one)

        Answer with ONLY the label, nothing else.
    """
    label = llm.invoke(prompt).content.strip().lower()
    return {"classification": label}

def get_specialist(state: AgentState):
    query = state['query']
    # Get available specialties from doctors
    available_specialties = list(set([d["specialty"] for d in Doctors]))
    
    prompt = f"""
        You are an assistant that helps users find medical professionals based on their symptoms.
        Given the user's symptoms, identify the medical specialty that would be most appropriate for their condition.
        
        Available specialties in our system: {available_specialties}
        
        User's query: {query}
        
        Based on the symptoms or condition described, return ONLY the specialty name from the available list above.
        If none match exactly, return the closest matching specialty from the list.
        Return ONLY the specialty name, nothing else.
    """
    specialty = llm.invoke(prompt).content.strip()
    return {"specialty": specialty}
def validate_specialty_match(state: AgentState):
    """Validate that the identified specialty matches available doctors in the system"""
    specialty = state.get("specialty", "")

    # Find doctors matching the specialty (case-insensitive)
    matching_doctors = [
        doctor for doctor in Doctors
        if specialty.lower() in doctor["specialty"].lower() or doctor["specialty"].lower() in specialty.lower()
    ]

    if matching_doctors:
        doctor_list = "\n".join([
            f"- {d['name']} ({d['specialty']}) - {d['location']}, ${d['Fee']}"
            for d in matching_doctors
        ])
        return {
            "professional_list": doctor_list,
            "message": f"Found {len(matching_doctors)} {specialty} specialist(s) available:\n{doctor_list}",
            "human_question": f"Found specialists for {specialty}. Would you like to:\n1. Choose a doctor from the list above\n2. Enter 'all' to see all professionals\n3. Provide additional criteria (location, max fee)"
        }
    else:
        # No exact match, show all available specialties
        all_specialties = list(set([d["specialty"] for d in Doctors]))
        all_doctors_list = "\n".join([
            f"- {d['name']} ({d['specialty']}) - {d['location']}, ${d['Fee']}"
            for d in Doctors
        ])
        return {
            "professional_list": all_doctors_list,
            "message": f"No {specialty} found in our system.\nAvailable specialties: {', '.join(all_specialties)}\n\nAll available professionals:\n{all_doctors_list}",
            "human_question": "No matching specialist found. Please choose from the available professionals above or describe different symptoms."
        }
 
@tool
def get_slots_for_weeks(professional_name: str, week_numbers: str) -> str:
    """Get available appointment slots for a professional for specified weeks.

    Args:
        professional_name: Name of the professional (Ali, Malik, Fatima, Sara, Mohamed)
        week_numbers: Comma-separated week numbers (e.g., "1,2" for current and next week)
    """
    weeks = [int(w.strip()) for w in week_numbers.split(",")]
    return get_available_slots_for_weeks(professional_name, weeks)

@tool
def book_appointment_slot(
        professional_name: str,
        client_name: str,
        day_of_week: str,
        start_time: str,
        week_number: int = 1
) -> str:
    """Book an appointment slot with a professional.

    Args:
        professional_name: Name of the professional
        client_name: Name of the client booking the appointment
        day_of_week: Day of the week (Monday, Tuesday, etc.)
        start_time: Start time in HH:MM format (e.g., 09:00)
        week_number: Week number (1 = current week, 2 = next week, etc.)
    """
    # Ensure week_number is int
    try:
        week_number = int(week_number)
    except ValueError:
        return f"Invalid week number: {week_number}"

    # Normalize start_time to HH:MM
    try:
        if ":" in start_time:
            h, m = start_time.split(":")
            start_time = f"{int(h):02d}:{int(m):02d}"
    except:
        pass

    professional = next(
        (p for p in Doctors if p["name"].lower() == professional_name.lower()),
        None
    )
    if not professional:
        return f"Professional {professional_name} not found."

    client = next(
        (c for c in CLIENTS if c["name"].lower() == client_name.lower()),
        None
    )
    if not client:
        return f"Client {client_name} not found."

    time_slot = next(
     (slot for slot in Doctors_TIMESLOTS
     if slot["professional_id"] == professional["id"]  # ✅ CORRECT
     and slot["dayofweek"].lower() == day_of_week.lower()
     and slot["start_time"] == start_time
     and slot["available"]),
    None
   )  

    if not time_slot:
        return f"Time slot not available for {professional_name} on {day_of_week} at {start_time}."

    today = datetime.now()
    current_week_start = today - timedelta(days=today.weekday())
    week_start = current_week_start + timedelta(weeks=week_number - 1)

    days_of_week_list = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    try:
        target_day_index = days_of_week_list.index(day_of_week.lower())
    except ValueError:
        return f"Invalid day of week: {day_of_week}"

    appointment_date = week_start + timedelta(days=target_day_index)
    date_str = appointment_date.strftime("%Y-%m-%d")
    
    existing_appointment = next(
    (apt for apt in APPOINTMENTS
     if apt["professional_id"] == professional["id"]  # ✅ CORRECT
     and apt["date"] == date_str
     and apt["start_time"] == start_time),
    None
)


    if existing_appointment:
        return f"This slot is already booked for {professional_name} on {date_str} at {start_time}."

    new_appointment = Appointment(
    id=len(APPOINTMENTS) + 1,
    professional_id=professional["id"],  # ✅ CORRECT
    client_id=client["id"],  # ✅ CORRECT
    start_time=time_slot["start_time"],  # ✅ CORRECT
    end_time=time_slot["end_time"],  # ✅ CORRECT
    duration=60,
    date=date_str
)


    APPOINTMENTS.append(new_appointment)

    return f"Appointment booked successfully for {client_name} with {professional_name} on {day_of_week}, {date_str} (Week {week_number}) at {start_time}-{time_slot['end_time']}."

def get_current_next_week_slots(state: AgentState):
    """Get available timeslots for current week and next week using agent"""
    query = state.get("query", "")
    professional_name = state.get("professional_name", "")

    prompt = """You are an appointment scheduling assistant.
    Use the get_slots_for_weeks tool to find available appointment slots.
    Extract the professional name from the query and get slots for weeks 1 and 2 (current and next week).
    Available professionals: Ali, Malik, Fatima, Sara, Mohamed
    Always pass week_numbers as "1,2" for current and next week.
    """

    agent = create_agent(
        model=llm,
        tools=[get_slots_for_weeks],
        system_prompt=prompt,
    )

    message = f"Find available slots for {professional_name}" if professional_name else query

    result = agent.invoke({
        "messages": [("user", message)]
    })

    response = result["messages"][-1].content

    # Extract professional name if not already set
    if not professional_name:
        extraction_prompt = f"""
            Extract the professional name from: {query}
            Available professionals: Ali, Malik, Fatima, Sara, Mohamed
            Return ONLY the name or "NONE".
        """
        professional_name = llm.invoke(extraction_prompt).content.strip()

    return {
        "timeslots": response,
        "professional_name": professional_name if professional_name.upper() != "NONE" else None,
        "message": response
    }


def find_professional(state: AgentState):
    """Ask user for professional search criteria"""
    specialty = state.get("specialty", "")
    professional_list = state.get("professional_list", "")
    
    if specialty and professional_list:
        return {"human_question": f"I found {specialty} specialists for you.\n\n{professional_list}\n\nWould you like to:\n1. Choose a doctor from the list above (enter their name)\n2. Add more criteria (e.g., location, max fee)\n3. Enter 'all' to see all professionals"}
    else:
        return {"human_question": "What are you looking for in a professional? (e.g., location, max fee, specialty)"}

@tool
def search_professionals(location: str = None, max_fee: int = None, specialty: str = None) -> str:
    """Search for professionals by location, maximum fee, and/or specialty.
    
    Args:
        location: City name (Beirut, Byblos, Saida, Tyre)
        max_fee: Maximum fee in dollars
        specialty: Medical specialty (Cardiology, Dermatology, Pediatrics, Neurology, Orthopedics)
    """
    matching = Doctors.copy()

    if location:
        matching = [p for p in matching if location.lower() in p["location"].lower()]

    if max_fee:
        matching = [p for p in matching if p["Fee"] <= max_fee]
    
    if specialty:
        matching = [p for p in matching if specialty.lower() in p["specialty"].lower() or p["specialty"].lower() in specialty.lower()]

    if not matching:
        return "No professionals found matching criteria."

    result = "Matching professionals:\n"
    for prof in matching:
        result += f"- {prof['name']} ({prof['specialty']}): {prof['location']}, ${prof['Fee']}\n"
    return result


def fetch_professionals(state: AgentState):
    """Fetch professionals based on user criteria using agent with tool"""
    criteria = state.get("professional_criteria", "")
    specialty = state.get("specialty", "")  # Get specialty from state if available

    prompt = f"""You are an assistant that helps users find professionals.
    Use the search_professionals tool to find professionals based on user criteria.
    Extract location, max_fee, and specialty from the user's request and pass them to the tool.
    If a specialty was already identified, use it: {specialty}
    Available specialties: Cardiology, Dermatology, Pediatrics, Neurology, Orthopedics
    Professionals: {[(d["name"], d["specialty"], d["location"], d["Fee"]) for d in Doctors]}
    """

    agent = create_agent(
        model=llm,
        tools=[search_professionals],
        system_prompt=prompt
    )

    search_query = criteria
    if specialty and specialty not in criteria:
        search_query = f"{criteria}, specialty: {specialty}"

    result = agent.invoke({
        "messages": [f"Find professionals matching: {search_query}"]
    })

    return {"professional_list": result["messages"][-1].content}



def get_specific_week_slots(state: AgentState):
    """Get available timeslots for a specific week using agent"""
    professional_name = state.get("professional_name")
    week_number = state.get("week_number", 1)

    if not professional_name:
        return {"message": "Professional name not set.", "timeslots": ""}

    prompt = """You are an appointment scheduling assistant.
    Use the get_slots_for_weeks tool to find available appointment slots.
    Extract the professional name and week number from the request.
    Available professionals: Ali, Malik, Fatima, Sara, Mohamed
    """

    agent = create_agent(
        model=llm,
        tools=[get_slots_for_weeks],
        system_prompt=prompt,
    )

    result = agent.invoke({
        "messages": [("user", f"Get available slots for {professional_name} for week {week_number}")]
    })

    response = result["messages"][-1].content

    return {
        "timeslots": response,
        "message": response
    }


def book_appointment(state: AgentState):
    """Book an appointment by directly calling the tool"""
    professional_name = state.get("professional_name")
    client_name = state.get("client_name")
    day_of_week = state.get("day_of_week")
    start_time = state.get("start_time")
    week_number = state.get("week_number", 1)

    if not all([professional_name, client_name, day_of_week, start_time]):
        return {"message": "Missing booking details. Please provide professional name, day, and time."}

    # Call the booking tool directly using invoke()
    response = book_appointment_slot.invoke({
        "professional_name": professional_name,
        "client_name": client_name,
        "day_of_week": day_of_week,
        "start_time": start_time,
        "week_number": week_number
    })

    return {
        "message": response
    }



def format_response(state: AgentState):
    """Format the final response"""
    formatted = f"""
    QUERY: {state['query']}
    
    RESULT:
    {state['message']}
    """
    return {"final_answer": formatted}


# Step 5: --------------------- Build Graph ---------------------
graph = StateGraph(AgentState)

# Add nodes
graph.add_node("node_init", init_node)
graph.add_node("node_classify", classify_question)
graph.add_node("node_get_specialist", get_specialist)
graph.add_node("node_validate_specialty", validate_specialty_match)
graph.add_node("node_get_current_next_week_slots", get_current_next_week_slots)
graph.add_node("node_find_professional", find_professional)
graph.add_node("node_fetch_professionals", fetch_professionals)
graph.add_node("node_specific_week_slots", get_specific_week_slots)
graph.add_node("node_book_appointment", book_appointment)
graph.add_node("node_final_format", format_response)

# Set entry point
graph.set_entry_point("node_init")

graph.add_edge("node_init", "node_classify")

# Step 6: --------------------- Routing Functions ---------------------
def route_classification(state: AgentState):
    """Route based on whether professional name exists in query"""
    return state["classification"]


def route_user_action(state: AgentState):
    """Route based on user's action: continue browsing, book, or quit"""
    action = state.get("user_action", "").lower()
    if action == "book":
        return "book"
    elif action == "quit":
        return "quit"
    else:  # continue or specific week number
        return "continue"


# Step 7: --------------------- Add Edges ---------------------
# Classification routes
graph.add_conditional_edges(
    "node_classify",
    route_classification,
    {
        "professional_exists": "node_get_current_next_week_slots",
        "professional_not_exists": "node_get_specialist",
    }
)
graph.add_edge("node_get_specialist", "node_validate_specialty")
graph.add_edge("node_validate_specialty", "node_find_professional")
# From find professional -> fetch professionals
graph.add_edge("node_find_professional", "node_fetch_professionals")

# From fetch professionals -> get current/next week slots
graph.add_edge("node_fetch_professionals", "node_get_current_next_week_slots")

# After showing current/next week slots, user decides what to do
graph.add_conditional_edges(
    "node_get_current_next_week_slots",
    route_user_action,
    {
        "continue": "node_specific_week_slots",
        "book": "node_book_appointment",
        "quit": "node_final_format",
    }
)

# Specific week node loops back to itself until user decides to book or quit
graph.add_conditional_edges(
    "node_specific_week_slots",
    route_user_action,
    {
        "continue": "node_specific_week_slots",  # Self-loop for browsing more weeks
        "book": "node_book_appointment",
        "quit": "node_final_format",
    }
)

# Book appointment -> final format
graph.add_edge("node_book_appointment", "node_final_format")

# Final format -> END
graph.add_edge("node_final_format", END)


# Step 8: ------------- Compile Graph ---------------------
app = graph.compile(
    checkpointer=memory,
    interrupt_before=["node_classify","node_find_professional", "node_fetch_professionals"],
    interrupt_after=["node_get_current_next_week_slots", "node_specific_week_slots"]
)

thread_config = {"configurable": {"thread_id": "case_101"}, "recursion_limit": 20}

#Step 9: ----------------- Run Example -----------------------------
if __name__ == "__main__":
    import time

    print("#" * 50)
    print("INTERACTIVE TEST CASE: Symptoms -> Specialty -> Book")
    print("#" * 50)

    thread_id = f"case_{int(time.time())}"
    thread_config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}

    # 1. Initial User Input
    query_input = input("Enter your symptoms (e.g., 'I have chest pain'): ")
    client_name_input = input("Enter your name: ")

    print(f"\n[System] Starting flow with query: {query_input}")

    # Start execution - stops before 'node_classify'
    app.invoke({
        "query": query_input,
        "client_name": client_name_input
    }, thread_config)

    # Resume to classify and find specialty - stops before 'node_find_professional'
    print("[System] Analyzing symptoms...")
    app.invoke(None, thread_config)

    # Retrieve state to show found specialists
    state = app.get_state(thread_config).values
    print("\n" + "=" * 50)
    print(f"SPECIALTY IDENTIFIED: {state.get('specialty', 'Unknown')}")
    print("=" * 50)
    print(state.get('message', ''))
    print("-" * 20)
    print(state.get('human_question', ''))

    # 2. User selects professional
    prof_choice = input("\nEnter professional name from list above: ")

    app.update_state(thread_config, {
        "professional_name": prof_choice,
        "professional_criteria": prof_choice
    })

    # Resume - runs 'node_find_professional', stops before 'node_fetch_professionals'
    app.invoke(None, thread_config)

    # Resume - runs 'node_fetch_professionals', runs 'node_get_current_next_week_slots', stops AFTER 'node_get_current_next_week_slots'
    print(f"\n[System] Fetching slots for {prof_choice}...")
    app.invoke(None, thread_config)

    # Retrieve state to show timeslots
    state = app.get_state(thread_config).values
    print("\n" + "=" * 50)
    print("AVAILABLE TIMESLOTS")
    print("=" * 50)
    print(state.get('timeslots', 'No slots found'))

    # 3. User books appointment
    action = input("\nDo you want to book? (yes/no): ").lower()

    if action in ["yes", "y", "book"]:
        day = input("Enter Day (e.g., Monday): ")
        time_str = input("Enter Time (e.g., 09:00): ")
        week = input("Enter Week Number (1 or 2): ")

        app.update_state(thread_config, {
            "user_action": "book",
            "day_of_week": day,
            "start_time": time_str,
            "week_number": int(week)
        })

        print("\n[System] Booking appointment...")
        app.invoke(None, thread_config)

        # Final result
        state = app.get_state(thread_config).values
        print("\n" + "=" * 50)
        print("FINAL RESULT")
        print("=" * 50)
        print(state.get('final_answer', state.get('message')))

    else:
        print("Exiting...")
print(APPOINTMENTS)

# if __name__ == "__main__":
#  print(book_appointment_slot(professional_name="ali", client_name="Malik", day_of_week="Monday", start_time="9:00", week_number=2))
