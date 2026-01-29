import streamlit as st
from google import genai
from google.genai import types
import io

# --- 1. CONFIG & SAFETY ---
st.set_page_config(page_title="Analyst Health Checker", page_icon="🏥", layout="wide")

# Custom CSS for UI
st.markdown("""
    <style> 
    .emergency-banner { background-color: #ff4b4b; color: white; padding: 20px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 20px; } 
    .stChatMessage { border-radius: 15px; }
    </style>
""", unsafe_allow_html=True)

# API Initialization
try:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("API Key not found in Streamlit Secrets.")
    st.stop()

# --- 2. SIDEBAR FEATURES (Location & File Upload) ---
with st.sidebar:
    st.title("🏥 Settings & Tools")
    
    # Feature: Location Integration
    user_state = st.selectbox(
        "Your Location (Nigeria)", 
        ["Lagos", "Abuja", "Kano", "Port Harcourt", "Ibadan", "Enugu", "Kaduna", "Other"]
    )
    
    st.divider()
    
    # Feature: PDF/Lab Report Upload
    st.subheader("📁 Upload Lab Report")
    uploaded_file = st.file_uploader("Upload a scan or PDF of your results", type=["pdf", "png", "jpg", "jpeg"])
    
    if uploaded_file:
        st.success("File uploaded! You can now ask the bot to explain these results.")

    st.divider()

    # Feature: History Download (Helper Logic)
    if "messages" in st.session_state and len(st.session_state.messages) > 0:
        st.subheader("📥 Save Consultation")
        chat_history = ""
        for msg in st.session_state.messages:
            chat_history += f"{msg['role'].upper()}: {msg['content']}\n\n"
        
        st.download_button(
            label="Download Chat History (TXT)",
            data=chat_history,
            file_name="health_consultation_history.txt",
            mime="text/plain"
        )

# --- 3. THE AI BRAIN ---
SYSTEM_INSTRUCTION = f"""
You are a Medical Triage Assistant for the Nigerian public. 
Current User Location: {user_state}, Nigeria.

- Understand local terms like 'internal heat', 'body peppered', 'malaria feelings'.
- If the user has chest pain, sudden numbness, or severe breathing issues, start your response with the word 'EMERGENCY'.
- If the user provides a lab report description, explain it in simple, non-scary terms but insist they see a doctor.
- Suggest government hospitals or healthcare centers specifically in {user_state}.
- Always categorize advice as: [EMERGENCY], [URGENT CONSULT], or [SELF-CARE/PHARMACY].
"""

# --- 4. MAIN CHAT UI ---
st.title("🚀 Analyst Health Checker Bot")
st.write(f"📍 Currently providing guidance for: **{user_state}**")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Interaction
if prompt := st.chat_input("Describe your symptoms or ask about your lab report..."):
    
    # If a file is uploaded, we prepend that context to the user's message
    full_prompt = prompt
    if uploaded_file:
        full_prompt = f"[User has uploaded a lab report/document]. User Question: {prompt}"

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # We pass the instruction and the messages to Gemini
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=st.session_state.messages,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
        )
        
        # Check for Emergency Red Flags
        if "EMERGENCY" in response.text.upper():
            st.markdown('<div class="emergency-banner">🚨 IMMEDIATE ACTION REQUIRED: Please proceed to the nearest Emergency Room or call 112.</div>', unsafe_allow_html=True)
        
        st.markdown(response.text)

        st.session_state.messages.append({"role": "assistant", "content": response.text})

# --- 5. LOGIC FOR ANALYST (Text or Vision) ---
if prompt := st.chat_input("Explain your symptoms to the Analyst..."):
    # 1. Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # 2. Prepare the payload
        # If no image is uploaded, 'input_data' is just the text prompt.
        input_data = [prompt]
        
        if uploaded_file:
            try:
                img = PIL.Image.open(uploaded_file)
                input_data.append(img)
            except Exception as e:
                st.warning("⚠️ Image detected but couldn't be read. Proceeding with text analysis.")

        try:
            # 3. Request analysis from Gemini
            # We use the current input + the System Instruction for context
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=input_data,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.7
                )
            )
            
            output_text = response.text
            
            # 4. Emergency UI Logic
            if "EMERGENCY" in output_text.upper():
                st.markdown('<div class="emergency-banner">🚨 EMERGENCY DETECTED: PLEASE SEEK IMMEDIATE MEDICAL ATTENTION.</div>', unsafe_allow_html=True)
            
            st.markdown(output_text)
            
            # 5. Save for history
            st.session_state.messages.append({"role": "assistant", "content": output_text})

        except Exception as e:
            st.error(f"📡 System Error: The Analyst is temporarily unavailable. ({str(e)[:50]}...)")
