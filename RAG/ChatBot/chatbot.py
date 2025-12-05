import streamlit as st
import os
from RAG.RAG_steps.embeddings import embed_texts
from RAG.RAG_steps.similarity import retrieve_relevant_chunks
from RAG.RAG_steps.prompt import prepare_prompt
from RAG.RAG_steps.call_llm import generate_answer
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
st.title("ChatBot answer based on Our Data🤖")



if "rag_collection" not in st.session_state:
    st.write("there is no data about the user)")
else:
    st.text_input("Please enter your message", key="user_msg", on_change=generate_response)






for m in  st.session_state.messages:
    if m['role'] == "user":
        st.write(f"🙎 ***You:*** '{m['content']}")
    else:
        st.write(f"🤖 ***AI:*** '{m['content']}")