import warnings
warnings.filterwarnings("ignore")

import streamlit as st
from google import genai
from google.genai import types
import re
import requests
from fpdf import FPDF

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="GenYatra | AI Travel Architect", page_icon="✈️", layout="wide")

# --- 2. CLOUD-SAFE API KEYS (Pulls from Streamlit Secrets) ---
SERPAPI_KEY = st.secrets.get("SERPAPI_KEY", "")
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "") 

# --- 3. CLEAN LUXURY DARK MODE CSS ---
st.markdown("""
    <style>
    #MainMenu, footer, header, [data-testid="stDecoration"] { display: none !important; }
    
    .stApp {
        background: linear-gradient(-45deg, #0B0F19, #111827, #1E1B4B, #000000) !important;
        background-size: 400% 400% !important;
        animation: gradientBG 15s ease infinite !important;
        height: 100vh;
    }
    
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    [data-testid="stAppViewContainer"], main, [data-testid="stBottomBlock"], [data-testid="stBottom"] { 
        background: transparent !important; background-color: transparent !important; 
    }
    
    [data-testid="stMarkdownContainer"] *, p, h1, h2, h3, h4, li, span, div { color: #F8FAFC !important; }
    
    [data-testid="stChatMessage"] { 
        background-color: rgba(15, 23, 42, 0.75) !important; 
        backdrop-filter: blur(16px) !important; 
        -webkit-backdrop-filter: blur(16px) !important;
        border-radius: 12px; padding: 24px; 
        border: 1px solid rgba(255, 255, 255, 0.1); 
        margin-bottom: 16px; 
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }
    
    [data-testid="stChatInput"] { background-color: rgba(0, 0, 0, 0.9) !important; border: 1px solid rgba(255, 255, 255, 0.2) !important; border-radius: 12px !important; }
    [data-testid="stChatInput"] textarea { color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; background-color: transparent !important; }
    [data-testid="stChatInput"] svg { fill: #FF9933 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 4. SIMPLE HEADER ---
st.markdown("""
    <div style='text-align: center; padding: 1rem 0; margin-bottom: 1rem;'>
        <h1 style='font-size: 3.5rem; font-weight: 900; letter-spacing: -1px; margin-bottom: 0px;'>✈️ GenYatra</h1>
        <p style='color: #FF9933 !important; font-size: 1.1rem; font-weight: 600; letter-spacing: 3px; text-transform: uppercase; margin-top: 5px;'>AI Travel Architect</p>
    </div>
""", unsafe_allow_html=True)

# --- 5. ADVANCED ROUND-TRIP FLIGHT ENGINE ---
def get_live_flights(origin, dest, out_date, ret_date):
    if not SERPAPI_KEY: return "### ✈️ Live Flight Data\n*Error: SerpApi Key missing in deployment secrets.*\n\n---\n\n"
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
            
            output = f"### ✈️ Live Round-Trip Flight Itinerary\n"
            output += f"**Total Price:** INR {price} (Round-Trip per person)\n\n"
            output += f"**🛫 Outbound Flight ({out_date}):**\n"
            output += f"- **Airline:** {out_airline}\n"
            output += f"- **Departure:** {out_dep[:16] if isinstance(out_dep, str) else out_dep}\n"
            output += f"- **Arrival:** {out_arr[:16] if isinstance(out_arr, str) else out_arr}\n\n"
            
            if len(flight.get("flights", [])) > 1:
                ret_flight = flight.get("flights", [])[-1]
                ret_airline = ret_flight.get("airline", out_airline)
                ret_dep = ret_flight.get("departure_airport", {}).get("time", "Unknown Time")
                ret_arr = ret_flight.get("arrival_airport", {}).get("time", "Unknown Time")
                output += f"**🛬 Return Flight ({ret_date}):**\n"
                output += f"- **Airline:** {ret_airline}\n"
                output += f"- **Departure:** {ret_dep[:16] if isinstance(ret_dep, str) else ret_dep}\n"
                output += f"- **Arrival:** {ret_arr[:16] if isinstance(ret_arr, str) else ret_arr}\n\n"
            else:
                output += f"**🛬 Return Flight ({ret_date}):**\n- Matches outbound airline. Check final booking for exact return timings.\n\n"
                
            output += "---\n\n"
            return output
        return f"### ✈️ Live Flight Data\n*No direct live pricing found for {out_date} to {ret_date}.*\n\n---\n\n"
    except Exception as e:
        return ""

# --- 6. SMART PDF FORMATTER ---
def create_pdf(text_content):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(11, 15, 25) 
    pdf.cell(0, 15, "GenYatra Master Itinerary", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.set_text_color(255, 153, 51) 
    pdf.cell(0, 10, "Your AI Travel Architect", ln=True, align='C')
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

# --- 7. AI INITIALIZATION & SYSTEM PROMPT ---
if not GEMINI_KEY:
    st.error("Deployment Error: Missing GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=GEMINI_KEY)

SYSTEM_PROMPT = """
You are GenYatra, an elite, PROACTIVE AI Travel Architect. Your job is to make planning effortless for the client.

CRITICAL DIRECTIVE ON DATES:
If a client says "March", DO NOT ask them for exact dates. YOU are the architect. Pick a reasonable 4 to 5 day block (e.g., March 12th to March 16th) on their behalf so you can run the live flight engine. Tell them: "I've selected March 12-16 to optimize your fares."

PHASE 1: THE QUICK INTERVIEW
You must know: Destination, Duration/Month, Who is traveling/Budget, and Transport Mode (If flight, get the Origin City).
DO NOT interrogate them endlessly. If they give you enough info in their first prompt, immediately generate the itinerary. 

PHASE 2: THE MASTER ITINERARY
- HOTEL LOGIC: You MUST explicitly change their hotel if they travel to a new region/city. Provide 3-5 real hotel options with estimated INR prices for every location change.
- RESTAURANTS: Name a REAL, specific restaurant for every meal with estimated INR prices.

PHASE 3: THE TOTAL TRIP ESTIMATE (CRITICAL)
At the very bottom of the itinerary, before the system tags, you MUST provide a "Total Estimated Budget" breakdown table.
It must include estimated costs for: 
1. Flights (Estimate it based on the route, noting live prices are at the top)
2. Hotels
3. Local Transport (Taxis, rentals)
4. Food & Dining
5. Activities & Passes
Total Estimated Trip Cost: INR [Sum]

SYSTEM TAGS (Output at the very bottom):
[FLIGHT_SEARCH: {ORIGIN_IATA}, {DESTINATION_IATA}, {YYYY-MM-DD}, {YYYY-MM-DD}] -> ONLY output this if they are flying. YOU must pick the YYYY-MM-DD dates if they only gave you a month. Assume year is 2026.
[PDF_READY] -> Output this tag at the very bottom of the completed itinerary.
"""

if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
    )
    st.session_state.messages = [{"role": "assistant", "content": "Welcome to GenYatra. Where are you dreaming of traveling to, and who will be joining you?", "hidden": False}]

for message in st.session_state.messages:
    if not message.get("hidden", False):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# --- 8. THE CONTINUOUS CHAT LOOP ---
user_input = st.chat_input("E.g., Plan a 4-day trip to Goa from Pune in March...")

if user_input:
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input, "hidden": False})
    
    with st.chat_message("assistant"):
        with st.spinner("GenYatra is securing your flights and architecting the trip..."):
            try:
                response = st.session_state.chat_session.send_message(user_input)
                clean_text = response.text
                live_flight_text = ""
                show_pdf_button = False
                
                flight_match = re.search(r'\[FLIGHT_SEARCH:\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^\]]+)\]', clean_text, re.IGNORECASE)
                if flight_match:
                    origin, dest, out_date, ret_date = flight_match.group(1).strip(), flight_match.group(2).strip(), flight_match.group(3).strip(), flight_match.group(4).strip()
                    live_flight_text = get_live_flights(origin, dest, out_date, ret_date)
                    clean_text = re.sub(r'\[FLIGHT_SEARCH:\s*[^\]]+\]', '', clean_text, flags=re.IGNORECASE).strip()

                if "[PDF_READY]" in clean_text:
                    show_pdf_button = True
                    clean_text = clean_text.replace("[PDF_READY]", "").strip()

                final_output = live_flight_text + clean_text
                
                st.session_state.messages.append({"role": "assistant", "content": final_output, "hidden": False})
                st.markdown(final_output)
                
                if show_pdf_button:
                    pdf_bytes = create_pdf(final_output)
                    st.download_button(
                        label="📄 Download Complete Itinerary (PDF)",
                        data=pdf_bytes,
                        file_name="GenYatra_Master_Itinerary.pdf",
                        mime="application/pdf",
                        key=f"pdf_btn_{len(st.session_state.messages)}"
                    )

            except Exception as e:
                st.error(f"Engine Failure: {str(e)}")
