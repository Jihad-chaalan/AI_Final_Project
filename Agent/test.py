# Update Agent/test.py to be continuous

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Agent.multi_agent import app, Doctors, CLIENTS

def print_header(title):
    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)

def continuous_chat():
    """Continuous conversation with the agent"""
    
    print("#" * 50)
    print("CONTINUOUS AGENT CHAT")
    print("Type 'quit' to exit, 'reset' to start over")
    print("#" * 50)
    
    # Show available resources
    print("\n📋 Available Doctors:")
    for doc in Doctors:
        print(f"  • {doc['name']} - {doc['specialty']} ({doc['location']}) - ${doc['Fee']}")
    
    print("\n👥 Available Clients:")
    for client in CLIENTS:
        print(f"  • {client['name']}")
    
    # Initialize
    thread_id = f"chat_{int(datetime.now().timestamp())}"
    thread_config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
    
    client_name = None
    current_state = None
    
    while True:
        print("\n" + "-" * 50)
        
        # Get client name if not set
        if not client_name:
            client_name = input("👤 Your name: ").strip()
            if client_name.lower() == 'quit':
                print("\n👋 Goodbye!")
                break
            continue
        
        # Get user input
        user_input = input(f"👤 {client_name}: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() == 'quit':
            print("\n👋 Goodbye!")
            break
        
        if user_input.lower() == 'reset':
            print("\n🔄 Starting new conversation...")
            thread_id = f"chat_{int(datetime.now().timestamp())}"
            thread_config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
            client_name = None
            current_state = None
            continue
        
        try:
            print("\n🤖 Agent: Processing...")
            
            # Check if we need to start new flow or continue existing
            if not current_state or current_state.get('final_answer'):
                # Start new booking flow
                print_header("STARTING NEW BOOKING")
                
                app.invoke({
                    "query": user_input,
                    "client_name": client_name
                }, thread_config)
                
                app.invoke(None, thread_config)
                
                state = app.get_state(thread_config).values
                current_state = state
                
                # Show response
                if state.get('classification') == "professional_not_exists":
                    print_header("AGENT FOUND SPECIALISTS")
                    
                    if state.get('specialty'):
                        print(f"Specialty: {state['specialty']}")
                    
                    if state.get('professional_list'):
                        print(f"\n{state['professional_list']}")
                    
                    if state.get('message'):
                        print(f"\n{state['message']}")
                    
                    print("\n🤖 Agent: Which doctor would you like? (Just type the name)")
                
                elif state.get('timeslots'):
                    print_header("AVAILABLE TIMESLOTS")
                    print(state['timeslots'])
                    print("\n🤖 Agent: Which slot? Format: <Day> <Time> <Week>")
                    print("         Example: Monday 09:00 2")
            
            else:
                # Continue existing flow
                state = current_state
                
                # Check if selecting professional
                if state.get('classification') == "professional_not_exists" and not state.get('timeslots'):
                    print_header("GETTING SLOTS")
                    
                    app.update_state(thread_config, {
                        "professional_name": user_input,
                        "professional_criteria": user_input
                    })
                    
                    app.invoke(None, thread_config)
                    
                    state = app.get_state(thread_config).values
                    current_state = state
                    
                    if state.get('timeslots'):
                        print_header("AVAILABLE TIMESLOTS")
                        print(state['timeslots'])
                        print("\n🤖 Agent: Which slot? Format: <Day> <Time> <Week>")
                        print("         Example: Monday 09:00 2")
                    else:
                        print("\n🤖 Agent: No slots available. Try another doctor or request.")
                        current_state = None
                
                # Check if booking
                elif state.get('timeslots') and not state.get('final_answer'):
                    # Parse booking: "Monday 09:00 2"
                    parts = user_input.split()
                    
                    if len(parts) >= 3:
                        day_of_week = parts[0]
                        start_time = parts[1]
                        week_number = int(parts[2])
                        
                        print_header("BOOKING APPOINTMENT")
                        print(f"Day: {day_of_week}, Time: {start_time}, Week: {week_number}")
                        
                        app.update_state(thread_config, {
                            "user_action": "book",
                            "day_of_week": day_of_week,
                            "start_time": start_time,
                            "week_number": week_number
                        })
                        
                        app.invoke(None, thread_config)
                        
                        state = app.get_state(thread_config).values
                        current_state = state
                        
                        print_header("BOOKING RESULT")
                        if state.get('message'):
                            print(state['message'])
                        
                        if state.get('final_answer'):
                            print(f"\n{state['final_answer']}")
                        
                        print("\n🤖 Agent: Need anything else? Or type a new request!")
                    else:
                        print("\n❌ Format: <Day> <Time> <Week>")
                        print("   Example: Monday 09:00 2")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            print("\nType 'reset' to start over or continue with a new request")
            current_state = None

if __name__ == "__main__":
    try:
        continuous_chat()
    except KeyboardInterrupt:
        print("\n\n👋 Chat ended!")