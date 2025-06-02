import streamlit as st
import google.generativeai as genai
import base64
import os
import re
from io import BytesIO
from xhtml2pdf import pisa
import markdown2

# --- Background Image Loader ---
def get_base64_image():
    for ext in ["webp", "jpg", "jpeg", "png"]:
        image_path = f"background.{ext}"
        if os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
    return None

bg_img = get_base64_image()

# --- Page Setup ---
st.set_page_config(page_title="Wellness Planner", layout="centered")

if bg_img:
    st.markdown(f"""
        <style>
        .stApp {{
            background: linear-gradient(rgba(255, 255, 255, 0.65), rgba(255, 255, 255, 0.85)),
                        url("data:image/png;base64,{bg_img}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        .block-container {{
            background-color: rgba(255, 248, 243, 0.45);
            padding: 2rem 3rem;
            border-radius: 18px;
            margin-top: 2rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #4B4B4B;
            font-family: 'Segoe UI', sans-serif;
        }}
        .export-buttons {{
            margin-top: 20px;
        }}
        </style>
    """, unsafe_allow_html=True)

# --- App Title ---
st.title("🧸 Wellness Planner for Autistic Children")

# --- API Configuration ---
genai.configure(api_key="AIzaSyBqx7s51Swc_l8jJILSjWjqyeNYvJXnFj0")

# --- State Initialization ---
if "step" not in st.session_state:
    st.session_state.step = 0
if "child_name" not in st.session_state:
    st.session_state.child_name = ""
if "child_age" not in st.session_state:
    st.session_state.child_age = ""
if "answers" not in st.session_state:
    st.session_state.answers = []
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Replay all messages ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Utilities ---
def chat_bot(message):
    with st.chat_message("assistant"):
        st.markdown(message)
    st.session_state.messages.append({"role": "assistant", "content": message})

def user_message(message):
    with st.chat_message("user"):
        st.markdown(message)
    st.session_state.messages.append({"role": "user", "content": message})

# --- Questions ---
questions = [
    "How does {name} behave in public settings?",
    "What are {name}'s favorite activities or interests?",
    "Does {name} follow a daily routine already?",
    "Is {name} sensitive to any sensory inputs (light, noise, texture)?",
    "Are there specific goals you'd like to achieve for {name} through this plan?"
]

# --- Initial Greeting ---
if st.session_state.step == 0:
    chat_bot("👋 Hey! I am your personal scheduler. Let's create a custom wellness plan together.")
    chat_bot("Please tell me your child's name and age (e.g., 'My child is Maya and she is 5').")
    st.session_state.step = 1

# --- Input Field ---
user_input = st.chat_input("Type your answer...")

# --- Main Logic ---
if user_input:
    user_message(user_input)

    # Step 1: Extract name and age
    if st.session_state.step == 1:
        name_match = re.search(r"(?:my child is|this is)\s+([A-Z][a-z]+)", user_input, re.IGNORECASE)
        age_match = re.search(r"(?:is|aged)?\s*(\d{1,2})", user_input)

        name = name_match.group(1) if name_match else "your child"
        age = age_match.group(1) if age_match else "unknown"

        st.session_state.child_name = name
        st.session_state.child_age = age
        chat_bot(f"Nice to meet you! {name} is {age} years old. Let’s continue.")
        chat_bot(questions[0].format(name=name))
        st.session_state.step = 2

    # Step 2+: Respond and ask next question
    elif st.session_state.step <= len(questions) + 1:
        answer = user_input
        st.session_state.answers.append(answer)

        prev_question = questions[st.session_state.step - 2].format(name=st.session_state.child_name)

        # Use Gemini to reply kindly to user input
        feedback_prompt = (
            f"You are a kind assistant helping a parent of an autistic child. "
            f"The parent answered this question:\n"
            f"Q: {prev_question}\n"
            f"A: {answer}\n"
            f"Reply with a short, kind, and encouraging sentence showing you understand."
        )

        model = genai.GenerativeModel("gemini-1.5-flash")
        feedback_response = model.generate_content(feedback_prompt)
        chat_bot(feedback_response.text.strip())

        # Ask next question or generate planner
        if st.session_state.step - 1 < len(questions):
            next_q = questions[st.session_state.step - 1].format(name=st.session_state.child_name)
            chat_bot(next_q)
            st.session_state.step += 1
        else:
            # All answers received – create plan
            prompt = f"Create a detailed weekly wellness plan for an autistic child named {st.session_state.child_name}, aged {st.session_state.child_age}.\n\n"
            for i, ans in enumerate(st.session_state.answers):
                prompt += f"{questions[i].format(name=st.session_state.child_name)}\nUser: {ans}\n\n"
            prompt += (
                "Generate a 7-day table (Mon–Sun) with columns: Morning, Afternoon, Evening, Night. "
                "Each cell should contain warm, autism-friendly structured activities. "
                "Follow with a brief narrative summary per day.\nAvoid generic advice. Be caring and personalized."
            )

            chat_bot("✅ Thanks! I'm generating your custom wellness planner...")

            response = model.generate_content(prompt)
            content = response.text.strip()
            chat_bot(content)

            # Convert Markdown to PDF
            def convert_markdown_to_pdf(md_text):
                html_body = markdown2.markdown(md_text)
                html = f"<html><body>{html_body}</body></html>"
                result = BytesIO()
                pisa.CreatePDF(html, dest=result)
                result.seek(0)
                return result

            pdf_data = convert_markdown_to_pdf(content)

            st.download_button(
                label="📄 Download Wellness Plan as PDF",
                data=pdf_data,
                file_name=f"{st.session_state.child_name}_wellness_plan.pdf",
                mime="application/pdf"
            )