import streamlit as st

page = st.navigation(
    [
        st.Page("RAG/ChatBot/chatbot.py", title="Chatbot", icon="🤖")
    ],
    position="top",
)

page.run()