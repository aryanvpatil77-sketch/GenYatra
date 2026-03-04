import warnings
warnings.filterwarnings("ignore")

import streamlit as st
from google import genai
from google.genai import types
import re
import requests
import time
from fpdf import FPDF

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="GenYatra | AI Travel Architect", layout="wide")

# --- 2. CLOUD-SAFE API KEYS (Pulls from Secrets) ---
SERPAPI_KEY = st.secrets.get("SERPAPI_KEY", "")
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "") 

# --- 3. THEME-AGNOSTIC MINIMALIST CSS ---
st.markdown("""
    <style>
    /* Hide Streamlit Clutter */
    #MainMenu, footer, header, [data-testid="stDecoration"] { display: none !important; }
    
    /* Make backgrounds transparent so they adapt to Streamlit's Light/Dark Mode natively */
    [data-testid="stAppViewContainer"], main, [data-testid="stBottomBlock"], [data-testid="stBottom"] { 
        background: transparent !important; background-color: transparent !important; 
    }
    
    /* Theme-Agnostic Chat Bubbles using subtle transparency */
    [data-testid="stChatMessage"] { 
        background-color: rgba(128, 128, 128, 0.05) !important; 
        border-radius: 8px; 
        padding: 20px; 
        border: 1px solid rgba(128, 128, 128, 0.2); 
        margin-bottom: 16px; 
    }
    
    /* Theme-Agnostic Input Box */
    [data-testid="stChatInput"] { 
        background-color: rgba(128, 128, 128, 0.03) !important; 
        border: 1px solid rgba(128, 128, 128, 0.2) !important; 
        border-radius: 8px !important; 
    }
    
    /* Header Branding - Color removed so it automatically flips black/white based on theme */
    .brand-title { 
        font-size: 3rem; font-weight: 800; letter-spacing: -1px; 
        text-align: center; margin-bottom: 0px; 
    }
    .brand-subtitle { 
        color: #64748B !important; font-size: 1rem; font-weight: 500; 
        letter-spacing: 4px; text-transform: uppercase; 
        text-align: center; margin-top: 5px; margin-bottom: 30px; 
    }
    </style>
""", unsafe_allow_html=True)

# --- 4. CLEAN PROFESSIONAL HEADER ---
st.markdown("<div class='brand-title'>GenYatra</div>", unsafe_allow_html=True)
st.markdown("<div class='brand-subtitle'>AI Travel Architect</div>", unsafe_allow_html=True)

# --- 5. DYNAMIC CONTEXTUAL AVATARS ---
def get_ai_icon(text):
    t = text.lower()
    if "itinerary" in t or "day 1" in t or "blueprint" in t: return ":material/description:" 
    if "destination" in t or "where" in t or "city" in t: return ":material/pin_drop:" 
    if "budget" in t or "cost" in t or "inr" in t: return ":material/payments:" 
    if "welcome" in t or "hello" in t: return ":material/waving_hand:" 
    return ":material/support_agent:" 

# --- 6. ADVANCED ROUND-TRIP FLIGHT ENGINE ---
def get_live_flights(origin, dest, out_date, ret_date):
    if not SERPAPI_KEY: return "### Live Flight Data\n*Error: SerpApi Key missing in deployment secrets.*\n\n---\n\n"
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_flights", "departure_id": origin, "arrival_id": dest,
        "outbound_date": out_date, "return_date": ret_date, "currency": "INR",
        "hl": "en", "type": "1", "api_key": SERPAPI_KEY
    }
    try:
        res = requests.get(url, params=params).json()
        if "best_flights" in res and len(res["best_flights"]) > 0:
            flight = res["best_flights"][0]
            price = flight.get("price", "Unknown")
            
            outbound = flight.get("flights", [{}])[0]
            out_airline = outbound.get("airline", "Unknown Airline")
            out_dep = outbound.get("departure_airport", {}).get("time", "Unknown Time")
            out_arr = outbound.get("arrival_airport", {}).get("time", "Unknown Time")
            
            output = f"### Live Round-Trip Flight Itinerary\n"
            output += f"**Total Price:** INR {price} (Round-Trip per person)\n\n"
            output += f"**Outbound Flight ({out_date}):**\n"
            output += f"- Airline: {out_airline}\n"
            output += f"- Departure: {out_dep[:16] if isinstance(out_dep, str) else out_dep}\n"
            output += f"- Arrival: {out_arr[:16] if isinstance(out_arr, str) else out_arr}\n\n"
            
            if len(flight.get("flights", [])) > 1:
                ret_flight = flight.get("flights", [])[-1]
                ret_airline = ret_flight.get("airline", out_airline)
                ret_dep = ret_flight.get("departure_airport", {}).get("time", "Unknown Time")
                ret_arr = ret_flight.get("arrival_airport", {}).get("time", "Unknown Time")
                output += f"**Return Flight ({ret_date}):**\n"
                output += f"- Airline: {ret_airline}\n"
                output += f"- Departure: {ret_dep[:16] if isinstance(ret_dep, str) else ret_dep}\n"
                output += f"- Arrival: {ret_arr[:16] if isinstance(ret_arr, str) else ret_arr}\n\n"
            else:
                output += f"**Return Flight ({ret_date}):**\n- Matches outbound airline.\n\n"
                
            output += "---\n\n"
            return output
        return f"### Live Flight Data\n*No direct live pricing found for {out_date} to {ret_date}.*\n\n---\n\n"
    except Exception as e:
        return ""

# --- 7. SMART PDF FORMATTER ---
def create_pdf(text_content):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(11, 15, 25) 
    pdf.cell(0, 15, "GenYatra Master Itinerary", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.set_text_color(100, 116, 139) 
    pdf.cell(0, 10, "AI Travel Architect", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_text_color(0, 0, 0) 
    
    clean_text = text_content.replace('₹', 'INR ').encode('ascii', 'ignore').decode('ascii')
    
    for line in clean_text.split('\n'):
        line = line.strip()
        if not line:
            pdf.ln(3)
            continue
        if line.startswith('### '):
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 15)
            pdf.multi_cell(0, 8, txt=line.replace('### ', ''))
            pdf.ln(2)
        elif line.startswith('**') and line.endswith('**'):
            pdf.set_font("Arial", 'B', 12)
            pdf.multi_cell(0, 7, txt=line.replace('**', ''))
        elif line.startswith('* **') or line.startswith('- **'):
            pdf.set_font("Arial", 'B', 11)
            pdf.multi_cell(0, 6, txt=line.replace('**', '').replace('* ', '- '))
        else:
            pdf.set_font("Arial", '', 11)
            pdf.multi_cell(0, 6, txt=line.replace('**', '').replace('*', '-'))
            
    return pdf.output(dest="S").encode("latin-1")

# --- 8. AI INITIALIZATION & SYSTEM PROMPT ---
if not GEMINI_KEY:
    st.error("Deployment Error: Missing GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=GEMINI_KEY)

SYSTEM_PROMPT = """
You are GenYatra, an elite, PROACTIVE AI Travel Architect. Your job is to make planning effortless for the client.
Do not use emojis in your responses. Keep your tone highly professional, concise, and consultative.

CRITICAL DIRECTIVE ON DATES:
If a client says "March", DO NOT ask them for exact dates. Pick a reasonable 4 to 5 day block (e.g., March 12th to March 16th) on their behalf to run the flight engine.

PHASE 1: THE QUICK INTERVIEW
You must know: Destination, Duration/Month, Who is traveling/Budget, and Transport Mode.
If they give you enough info in their first prompt, immediately generate the itinerary. 

PHASE 2: THE MASTER ITINERARY
- HOTEL LOGIC: You MUST explicitly change their hotel if they travel to a new region/city. Provide 3-5 real hotel options.
- RESTAURANTS: Name a REAL, specific restaurant for every meal.

PHASE 3: THE TOTAL TRIP ESTIMATE
At the bottom, provide a "Total Estimated Budget" breakdown table.

SYSTEM TAGS:
[FLIGHT_SEARCH: {ORIGIN_IATA}, {DESTINATION_IATA}, {YYYY-MM-DD}, {YYYY-MM-DD}] -> ONLY output this if they are flying. Assume year is 2026.
[PDF_READY] -> Output this tag at the very bottom.
"""

if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
    )
    st.session_state.messages = [{"role": "assistant", "content": "Welcome to GenYatra. Where are you dreaming of traveling to, and who will be joining you?", "icon": ":material/waving_hand:"}]

for message in st.session_state.messages:
    icon = message.get("icon", ":material/person:") if message["role"] == "assistant" else ":material/person:"
    with st.chat_message(message["role"], avatar=icon):
        st.markdown(message["content"])

# --- 9. THE CONTINUOUS CHAT LOOP ---
user_input = st.chat_input("E.g., Plan a 4-day trip to Goa from Pune in March...")

if user_input:
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input, "icon": ":material/person:"})
    
    with st.chat_message("assistant", avatar=":material/psychology:"):
        with st.status("Analyzing your travel preferences...", expanded=True) as status:
            time.sleep(1) 
            
            try:
                status.update(label="Architecting your personalized itinerary...", state="running")
                response = st.session_state.chat_session.send_message(user_input)
                clean_text = response.text
                live_flight_text = ""
                show_pdf_button = False
                
                flight_match = re.search(r'\[FLIGHT_SEARCH:\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^\]]+)\]', clean_text, re.IGNORECASE)
                if flight_match:
                    status.update(label="Searching live flight fares & timings...", state="running")
                    origin, dest, out_date, ret_date = flight_match.group(1).strip(), flight_match.group(2).strip(), flight_match.group(3).strip(), flight_match.group(4).strip()
                    live_flight_text = get_live_flights(origin, dest, out_date, ret_date)
                    clean_text = re.sub(r'\[FLIGHT_SEARCH:\s*[^\]]+\]', '', clean_text, flags=re.IGNORECASE).strip()

                if "[PDF_READY]" in clean_text:
                    show_pdf_button = True
                    clean_text = clean_text.replace("[PDF_READY]", "").strip()

                final_output = live_flight_text + clean_text
                
                status.update(label="Finalizing travel blueprint...", state="complete", expanded=False)
                
            except Exception as e:
                status.update(label="Engine Failure", state="error", expanded=False)
                st.error(f"Error: {str(e)}")
                st.stop()
        
        def stream_data(text):
            for word in text.split(" "):
                yield word + " "
                time.sleep(0.02)
                
        st.write_stream(stream_data(final_output))
        final_ai_icon = get_ai_icon(final_output)
        st.session_state.messages.append({"role": "assistant", "content": final_output, "icon": final_ai_icon})
        
        if show_pdf_button:
            pdf_bytes = create_pdf(final_output)
            st.download_button(
                label="Download Master Itinerary (PDF)",
                data=pdf_bytes,
                file_name="GenYatra_Master_Itinerary.pdf",
                mime="application/pdf",
                key=f"pdf_btn_{len(st.session_state.messages)}"
            )
