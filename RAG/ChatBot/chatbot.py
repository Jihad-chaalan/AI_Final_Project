import streamlit as st
import os
from RAG.RAG_steps.embeddings import embed_texts
from RAG.RAG_steps.similarity import retrieve_relevant_chunks
from RAG.RAG_steps.prompt import prepare_prompt
from RAG.RAG_steps.call_llm import generate_answer
from RAG.RAG_steps.vector_db import get_db_collection
from dotenv import load_dotenv
load_dotenv()

# st.write(os.getenv("DEEPSEEK_API_KEY"))

if "messages" not in st.session_state:
    st.session_state.messages = []


def generate_response():
    user_msg = st.session_state.user_msg 


    question_vector = embed_texts([st.session_state.user_msg])

    #step 6: perform semantic / similarity search to get relevant chunks
    result = retrieve_relevant_chunks(question_vector, st.session_state.rag_collection, 3) #pick only top 3

    #step 7: prepare a prompt
    prompt = prepare_prompt(st.session_state.user_msg, result['documents'][0])   
    #step 8: call deepseek and get an answer
    answer = generate_answer(prompt, os.getenv("DEEPSEEK_API_KEY"))
   
    st.session_state.messages.append({
        "role":"user",
        "content": {user_msg}
    })
    if answer:
        st.session_state.messages.append({
        "role":"AI",
        "content": {answer}
        })
    else:
        st.session_state.messages.append({
        "role":"AI",
        "content": "There is an error, Please Try Again later"
        })
    st.session_state.user_msg = ""

#step 5: write query and generate the embeddings of the query
# user_question = input("Enter your questions / query here: whats in your mind today?")
# question_list = []
# question_list.append(user_question)


#####ChatBot Page####
st.title("ChatBot answer based on Our the Data of the patients🤖🩺")



# Initialize the collection from ChromaDB if not in session state
if "rag_collection" not in st.session_state:
    # Try to load existing collection from ChromaDB
    try:
        st.session_state.rag_collection = get_db_collection()
        # Check if the collection has any data
        if st.session_state.rag_collection.count() == 0:
            st.warning("⚠️ No documents found in the database. Please upload documents in the Load page first.")
        else:
            st.success(f"✅ Loaded {st.session_state.rag_collection.count()} chunks from database")
    except Exception as e:
        st.error(f"❌ Error loading collection: {e}")
        st.stop()

# Only show the chat interface if we have data
if st.session_state.rag_collection.count() > 0:
    st.text_input("Please enter your message", key="user_msg", on_change=generate_response)
    
    for m in st.session_state.messages:
        if m['role'] == "user":
            st.write(f"🙎 ***You:*** '{m['content']}")
        else:
            st.write(f"🤖 ***AI:*** '{m['content']}")
else:
    st.info("📂 Please go to the **Load** page and upload some documents first to start chatting!")