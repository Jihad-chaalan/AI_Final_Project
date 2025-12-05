from langchain.agents import create_agent
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Schema.Data import PROFESSIONALS, PROFESSIONALS_TIMESLOTS, APPOINTMENTS, CLIENTS
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


llm = get_gemini()


# Step 2: -------------------- State Definition ---------------------
class AgentState(TypedDict):
    professional_name: str | None
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
        (p for p in PROFESSIONALS if p["name"].lower() == professional_name.lower()),
        None
    )

    if not professional:
        return f"Professional {professional_name} not found."

    prof_timeslots = [
        slot for slot in PROFESSIONALS_TIMESLOTS
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
def classify_question(state: AgentState):
    """Classify if the query mentions a professional name"""
    prompt = f"""
        You are a classifier for appointment booking queries.

        Available professionals in the system: Ali, Malik, Fatima, Sara, Mohamed

        Task: Determine if the user's query mentions a specific professional's name from the list above.

        Question: {state['query']}

        Classify as EXACTLY ONE of these labels:
        - 'professional_exists' (if a specific professional name from the list is mentioned)
        - 'professional_not_exists' (if no professional name is mentioned or asking for help to find one)

        Answer with ONLY the label, nothing else.
    """
    label = llm.invoke(prompt).content.strip().lower()
    return {"classification": label}

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
    professional = next(
        (p for p in PROFESSIONALS if p["name"].lower() == professional_name.lower()),
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
        (slot for slot in PROFESSIONALS_TIMESLOTS
         if slot["professional_id"] == professional["id"]
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
    target_day_index = days_of_week_list.index(day_of_week.lower())

    appointment_date = week_start + timedelta(days=target_day_index)
    date_str = appointment_date.strftime("%Y-%m-%d")

    existing_appointment = next(
        (apt for apt in APPOINTMENTS
         if apt["professional_id"] == professional["id"]
         and apt["date"] == date_str
         and apt["start_time"] == start_time),
        None
    )

    if existing_appointment:
        return f"This slot is already booked for {professional_name} on {date_str} at {start_time}."

    new_appointment = Appointment(
        id=len(APPOINTMENTS) + 1,
        professional_id=professional["id"],
        client_id=client["id"],
        start_time=time_slot["start_time"],
        end_time=time_slot["end_time"],
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
    return {"human_question": "What are you looking for in a professional? (e.g., location, max fee)"}

@tool
def search_professionals(location: str = None, max_fee: int = None) -> str:
    """Search for professionals by location and/or maximum fee.
    
    Args:
        location: City name (Beirut, Byblos, Saida, Tyre)
        max_fee: Maximum fee in dollars
    """
    matching = PROFESSIONALS.copy()

    if location:
        matching = [p for p in matching if location.lower() in p["location"].lower()]

    if max_fee:
        matching = [p for p in matching if p["Fee"] <= max_fee]

    if not matching:
        return "No professionals found matching criteria."

    result = "Matching professionals:\n"
    for prof in matching:
        result += f"- {prof['name']}: {prof['location']}, ${prof['Fee']}\n"
    return result


def fetch_professionals(state: AgentState):
    """Fetch professionals based on user criteria using agent with tool"""
    criteria = state.get("professional_criteria", "")

    prompt = f"""You are an assistant that helps users find professionals.
    Use the search_professionals tool to find professionals based on user criteria.
    Extract location and max_fee from the user's request and pass them to the tool.
    Professionals:{PROFESSIONALS}
    """

    agent = create_agent(
        model=llm,
        tools=[search_professionals],
        system_prompt=prompt
    )

    result = agent.invoke({
        "messages": [f"Find professionals matching: {criteria}"]
    })

    return {"professional_list": result["messages"][-1].content}



def get_specific_week_slots(state: AgentState):
    """Get available timeslots for a specific week using agent"""
    professional_name = state.get("professional_name")
    week_number = state.get("week_number", 1)

    if not professional_name:
        return {"message": "Professional name not set.", "timeslots": ""}

    prompt = f"""You are an assistant that helps users find professionals.
    Use the search_professionals tool to find professionals based on user criteria.
    Extract location and max_fee from the user's request and pass them to the tool.
    If no specific criteria are provided, call the tool with no parameters to list all professionals.
    Do NOT ask follow-up questions - use whatever information is available.
    Professionals:{PROFESSIONALS}
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
    """Book an appointment using agent with tool"""
    professional_name = state.get("professional_name")
    client_name = state.get("client_name")
    day_of_week = state.get("day_of_week")
    start_time = state.get("start_time")
    week_number = state.get("week_number", 1)

    if not all([professional_name, client_name, day_of_week, start_time]):
        return {"message": "Missing booking details. Please provide professional name, day, and time."}

    prompt = """You are an appointment booking assistant.
    Use the book_appointment_slot tool to book appointments.
    Extract all required parameters from the user request:
    - professional_name
    - client_name
    - day_of_week (Monday, Tuesday, etc.)
    - start_time (HH:MM format)
    - week_number (default 1 for current week)
    """

    agent = create_agent(
        model=llm,
        tools=[book_appointment_slot],
        system_prompt=prompt,
    )

    result = agent.invoke({
        "messages": [(
            "user",
            f"Book appointment for {client_name} with {professional_name} on {day_of_week} at {start_time} for week {week_number}"
        )]
    })

    response = result["messages"][-1].content

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
graph.add_node("node_classify", classify_question)
graph.add_node("node_get_current_next_week_slots", get_current_next_week_slots)
graph.add_node("node_find_professional", find_professional)
graph.add_node("node_fetch_professionals", fetch_professionals)
graph.add_node("node_specific_week_slots", get_specific_week_slots)
graph.add_node("node_book_appointment", book_appointment)
graph.add_node("node_final_format", format_response)

# Set entry point
graph.set_entry_point("node_classify")


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
        "professional_not_exists": "node_find_professional",
    }
)

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
    interrupt_before=["node_find_professional", "node_fetch_professionals"],
    interrupt_after=["node_get_current_next_week_slots", "node_specific_week_slots"]
)

thread_config = {"configurable": {"thread_id": "case_101"}, "recursion_limit": 20}


# Step 9: ----------------- Run Example -----------------------------
if __name__ == "__main__":
    import time
    
    # Scenario 1: Booking with a known professional
    print("#" * 50)
    print("SCENARIO 1: Booking with a known professional")
    print("#" * 50)
    
    thread_id = f"case_{int(time.time())}"
    thread_config_1 = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
    
    app.invoke({
        "query": "help me take an appointment with Ali",
        "client_name": "Malik"
    }, thread_config_1)
    
    print("\n" + "=" * 50)
    print("AVAILABLE APPOINTMENTS (Current Week & Next Week)")
    print("=" * 50)
    print(app.get_state(thread_config_1).values["timeslots"])
    
    # Loop for specific week selection
    while True:
        user_choice = input("\nOptions:\n  - Enter a week number (1 is the current week) to see that week's slots\n  - Type 'book' to book an appointment\n  - Type 'quit' to exit\nYour choice: ").strip().lower()
        
        if user_choice == "quit":
            app.update_state(thread_config_1, {"user_action": "quit", "message": "User chose to exit."})
            app.invoke(None, thread_config_1)
            print("\nExited.")
            break
        elif user_choice == "book":
            # Booking loop with confirmation
            while True:
                week_num = input("Enter week number for booking: ")
                day_input = input("Enter day of week (e.g., Monday, Thursday): ")
                time_input = input("Enter start time (e.g., 09:00, 11:00): ")
                
                # Show confirmation prompt
                print("\n" + "-" * 40)
                print("APPOINTMENT DETAILS:")
                print(f"  Week: {week_num}")
                print(f"  Day: {day_input}")
                print(f"  Time: {time_input}")
                print("-" * 40)
                
                confirm = input("\nConfirm booking? (yes/no/change_week): ").strip().lower()
                
                if confirm == "yes":
                    app.update_state(thread_config_1, {
                        "user_action": "book",
                        "week_number": int(week_num),
                        "day_of_week": day_input,
                        "start_time": time_input
                    })
                    app.invoke(None, thread_config_1)
                    print("\n" + "=" * 50)
                    print("BOOKING CONFIRMATION")
                    print("=" * 50)
                    print(app.get_state(thread_config_1).values["final_answer"])
                    break
                elif confirm == "change_week":
                    # Show available weeks and let user pick a different week
                    new_week = input("Enter new week number to view slots: ")
                    try:
                        app.update_state(thread_config_1, {
                            "user_action": "continue",
                            "week_number": int(new_week)
                        })
                        app.invoke(None, thread_config_1)
                        print("\n" + "=" * 50)
                        print(f"AVAILABLE APPOINTMENTS (Week {new_week})")
                        print("=" * 50)
                        print(app.get_state(thread_config_1).values["timeslots"])
                    except ValueError:
                        print("Invalid week number.")
                    # Continue the booking loop
                else:
                    # User said no, repeat day/time entry
                    print("\nPlease re-enter appointment details.")
                    continue
            break
        else:
            # Assume it's a week number
            try:
                week_num = int(user_choice)
                app.update_state(thread_config_1, {
                    "user_action": "continue",
                    "week_number": week_num
                })
                app.invoke(None, thread_config_1)
                
                print("\n" + "=" * 50)
                print(f"AVAILABLE APPOINTMENTS (Week {week_num})")
                print("=" * 50)
                print(app.get_state(thread_config_1).values["timeslots"])
            except ValueError:
                print("Invalid input. Please enter a week number, 'book', or 'quit'.")
    
    print("\n" + "#" * 50)
    print("SCENARIO 2: Finding and booking with a professional")
    print("#" * 50)
    
    thread_id_2 = f"case_{int(time.time())}_2"
    thread_config_2 = {"configurable": {"thread_id": thread_id_2}, "recursion_limit": 20}
    
    app.invoke({
        "query": "help me take an appointment",
        "client_name": "Malik"
    }, thread_config_2)
    
    # Continue to get the human question
    app.invoke(None, thread_config_2)
    
    print(f"\n{app.get_state(thread_config_2).values['human_question']}")
    
    criteria = input("\nEnter professional criteria (e.g., 'Beirut', 'max fee 80'): ")
    
    app.update_state(thread_config_2, {"professional_criteria": criteria})
    app.invoke(None, thread_config_2)
    
    print("\n" + "=" * 50)
    print("MATCHING PROFESSIONALS")
    print("=" * 50)
    print(app.get_state(thread_config_2).values["professional_list"])
    
    professional_name = input("\nEnter the professional name you want: ")
    
    app.update_state(thread_config_2, {"professional_name": professional_name}, as_node="node_fetch_professionals")
    app.invoke(None, thread_config_2)
    
    print("\n" + "=" * 50)
    print("AVAILABLE APPOINTMENTS (Current Week & Next Week)")
    print("=" * 50)
    print(app.get_state(thread_config_2).values["timeslots"])
    
    # Loop for specific week selection
    while True:
        user_choice = input("\nOptions:\n  - Enter a week number (1 is the current week) to see that week's slots\n  - Type 'book' to book an appointment\n  - Type 'quit' to exit\nYour choice: ").strip().lower()
        
        if user_choice == "quit":
            app.update_state(thread_config_2, {"user_action": "quit", "message": "User chose to exit."})
            app.invoke(None, thread_config_2)
            print("\nExited.")
            break
        elif user_choice == "book":
            # Booking loop with confirmation
            while True:
                week_num = input("Enter week number for booking: ")
                day_input = input("Enter day of week (e.g., Monday, Thursday): ")
                time_input = input("Enter start time (e.g., 09:00, 11:00): ")
                
                # Show confirmation prompt
                print("\n" + "-" * 40)
                print("APPOINTMENT DETAILS:")
                print(f"  Week: {week_num}")
                print(f"  Day: {day_input}")
                print(f"  Time: {time_input}")
                print("-" * 40)
                
                confirm = input("\nConfirm booking? (yes/no/change_week): ").strip().lower()
                
                if confirm == "yes":
                    app.update_state(thread_config_2, {
                        "user_action": "book",
                        "week_number": int(week_num),
                        "day_of_week": day_input,
                        "start_time": time_input
                    })
                    app.invoke(None, thread_config_2)
                    print("\n" + "=" * 50)
                    print("BOOKING CONFIRMATION")
                    print("=" * 50)
                    print(app.get_state(thread_config_2).values["final_answer"])
                    break
                elif confirm == "change_week":
                    # Show available weeks and let user pick a different week
                    new_week = input("Enter new week number to view slots: ")
                    try:
                        app.update_state(thread_config_2, {
                            "user_action": "continue",
                            "week_number": int(new_week)
                        })
                        app.invoke(None, thread_config_2)
                        print("\n" + "=" * 50)
                        print(f"AVAILABLE APPOINTMENTS (Week {new_week})")
                        print("=" * 50)
                        print(app.get_state(thread_config_2).values["timeslots"])
                    except ValueError:
                        print("Invalid week number.")
                    # Continue the booking loop
                else:
                    # User said no, repeat day/time entry
                    print("\nPlease re-enter appointment details.")
                    continue
            break
        else:
            try:
                week_num = int(user_choice)
                app.update_state(thread_config_2, {
                    "user_action": "continue",
                    "week_number": week_num
                })
                app.invoke(None, thread_config_2)
                
                print("\n" + "=" * 50)
                print(f"AVAILABLE APPOINTMENTS (Week {week_num})")
                print("=" * 50)
                print(app.get_state(thread_config_2).values["timeslots"])
            except ValueError:
                print("Invalid input. Please enter a week number, 'book', or 'quit'.")
