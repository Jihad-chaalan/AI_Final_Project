import streamlit as st

page = st.navigation(
    [
        st.Page("RAG/ChatBot/chatbot.py", title="Chatbot", icon="🤖"),
        st.Page("RAG/Load/load.py", title="Load", icon="📂"),
         st.Page("Dashboard/dashboard.py", title="Dashboard", icon="📊"),
        st.Page("Agent/agent_streamlit.py", title="Book Appointment", icon="🏥"),
         
    ],
    position="top",
)

page.run()