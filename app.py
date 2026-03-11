import warnings
warnings.filterwarnings("ignore")

import streamlit as st
from google import genai
from google.genai import types
import re
import requests
import time
import os
import base64
from fpdf import FPDF

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="GenYatra | AI Travel Architect", layout="wide", initial_sidebar_state="expanded")

# --- 2. LOGO INTEGRATION ---
LOGO_FILE = "logo.jpeg"
encoded_logo = ""
if os.path.exists(LOGO_FILE):
    with open(LOGO_FILE, "rb") as image_file:
        encoded_logo = base64.b64encode(image_file.read()).decode()

# --- 3. DEPLOYMENT API KEYS ---
SERPAPI_KEY = st.secrets.get("SERPAPI_KEY", "")
GEMINI_KEY = st.secrets.get("GEMINI_KEY", st.secrets.get("GEMINI_API_KEY", "")) 
FIREBASE_API_KEY = st.secrets.get("FIREBASE_API_KEY", "")
FIREBASE_DB_URL = st.secrets.get("FIREBASE_DB_URL", "")

# --- 4. PREMIUM THEME-AGNOSTIC CSS (Alignment & Sidebar Toggle Fixes) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&display=swap');
    
    * { font-family: 'Google Sans', -apple-system, BlinkMacSystemFont, sans-serif !important; }

    /* Hide Clutter but KEEP the header transparent so the Sidebar Toggle remains visible! */
    #MainMenu, footer, [data-testid="stDecoration"] { display: none !important; }
    header { background: transparent !important; box-shadow: none !important; }
    
    [data-testid="stAppViewContainer"], main, [data-testid="stBottomBlock"], [data-testid="stBottom"] { 
        background: transparent !important; background-color: transparent !important; 
    }
    
    .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }
    [data-testid="InputInstructions"] { display: none !important; }
    
    /* Animations */
    @keyframes slideUpFade {
        0% { opacity: 0; transform: translateY(20px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    .anim-1 { animation: slideUpFade 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) forwards; }
    .anim-2 { animation: slideUpFade 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) 0.1s forwards; opacity: 0; }
    .anim-3 { animation: slideUpFade 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) 0.2s forwards; opacity: 0; }

    /* Login Page Styling */
    .brand-container { text-align: center; margin-top: 0vh; margin-bottom: 20px; }
    .welcome-to { color: #FF9933 !important; font-size: 1.1rem; font-weight: 600; letter-spacing: 2px; text-transform: lowercase; margin-bottom: 10px; }
    .login-logo { max-width: 220px; margin: 0 auto 20px auto; display: block; }
    
    .auth-header-professional { font-size: 2.2rem; font-weight: 700; color: inherit; text-align: center; margin-bottom: 5px; }
    .auth-subtitle { opacity: 0.6; font-size: 1.05rem; text-align: center; margin-bottom: 30px; }
    .divider { text-align: center; opacity: 0.4; margin: 20px 0; font-size: 0.85rem; font-weight: 600; }

    /* Home Screen Typography */
    .gemini-greeting { 
        font-size: 3.5rem; font-weight: 500; 
        background: -webkit-linear-gradient(74deg, #4285f4 0, #9b72cb 9%, #d96570 20%, #d96570 24%, #9b72cb 35%, #4285f4 44%, #9b72cb 50%, #d96570 56%, #131314 75%, #131314 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
        margin-bottom: 5px; text-align: left; line-height: 1.2;
    }
    @media (prefers-color-scheme: dark) {
        .gemini-greeting {
            background: -webkit-linear-gradient(74deg, #8ab4f8 0, #c58af9 9%, #f28b82 20%, #f28b82 24%, #c58af9 35%, #8ab4f8 44%, #c58af9 50%, #f28b82 56%, #e8eaed 75%, #e8eaed 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
        }
    }
    .gemini-greeting-sub { 
        font-size: 3.5rem; opacity: 0.6; font-weight: 400; 
        margin-top: 0px; margin-bottom: 50px; text-align: left; line-height: 1.2;
    }

    /* --- THE MASSIVE SEARCH PILL --- */
    [data-testid="stForm"] { 
        background-color: rgba(128, 128, 128, 0.08) !important; 
        border-radius: 40px !important; 
        padding: 5px 15px 5px 25px !important; 
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02) !important;
    }
    
    [data-testid="stForm"] > div,
    [data-testid="stForm"] div[data-baseweb="input"],
    [data-testid="stForm"] div[data-baseweb="base-input"],
    [data-testid="stForm"] div[data-testid="stTextInput"] > div {
        background-color: transparent !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    /* ALIGNMENT FIX: Nuke the invisible ghost label that shifts text down */
    [data-testid="stForm"] label { display: none !important; }
    
    /* The Text Input itself */
    [data-testid="stForm"] input {
        background-color: transparent !important;
        border: none !important;
        font-size: 1.15rem !important;
        padding: 12px 0px !important; /* Matched perfectly with button */
        margin: 0px !important;
        box-shadow: none !important;
        color: inherit !important;
    }
    [data-testid="stForm"] input::placeholder { opacity: 0.5; font-weight: 400; }
    [data-testid="stForm"] input:focus { border: none !important; box-shadow: none !important; background-color: transparent !important; }

    /* The "Plan" Button Container & Button */
    div[data-testid="stFormSubmitButton"] {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        margin: 0px !important;
        padding: 0px !important;
    }
    div[data-testid="stFormSubmitButton"] button {
        background-color: transparent !important; color: #1A73E8 !important; border: none !important;
        border-radius: 50px !important; font-weight: 600 !important; font-size: 1.1rem !important;
        margin: 0px !important; 
        padding: 12px 20px !important; /* Matched perfectly with input */
        align-self: center;
    }
    div[data-testid="stFormSubmitButton"] button:hover { background-color: rgba(128, 128, 128, 0.1) !important; }

    /* --- SIDEBAR PREMIUM UPGRADE --- */
    [data-testid="stSidebar"] {
        background-color: rgba(128,128,128,0.02) !important;
        border-right: 1px solid rgba(128,128,128,0.1) !important;
    }
    
    .profile-badge {
        display: flex; align-items: center; gap: 12px; padding: 12px 15px;
        background-color: rgba(128,128,128,0.05); border-radius: 12px;
        margin-bottom: 25px; border: 1px solid rgba(128,128,128,0.15);
    }
    .profile-avatar {
        width: 38px; height: 38px; border-radius: 50%;
        background: linear-gradient(135deg, #1A73E8, #9b72cb);
        color: white; display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 1.1rem;
    }
    
    [data-testid="stSidebar"] button[kind="secondary"] {
        border: 1px solid rgba(128,128,128,0.2) !important;
        border-radius: 10px !important;
        transition: all 0.2s ease !important;
        font-weight: 500 !important;
        padding: 10px !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"]:hover {
        border-color: #1A73E8 !important;
        color: #1A73E8 !important;
        background-color: rgba(26,115,232,0.05) !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        border: 1px solid rgba(128,128,128,0.15) !important;
        border-radius: 10px !important;
        background-color: rgba(128,128,128,0.03) !important;
    }

    /* --- LOGO THEME ADAPTATION --- */
    [data-testid="stSidebar"] img, .login-logo, .home-logo {
        transition: filter 0.3s ease;
    }
    @media (prefers-color-scheme: dark) {
        [data-testid="stSidebar"] img, .login-logo, .home-logo {
            filter: brightness(0) invert(1) !important; 
        }
    }
    
    .login-btn-container [data-testid="stTextInput"] > div {
        border-radius: 8px;
        border: 1px solid rgba(128, 128, 128, 0.3);
        background-color: rgba(128, 128, 128, 0.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. FIREBASE LOGIC ---
def sign_up(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    res = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})
    return res.json()

def sign_in(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    res = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})
    return res.json()

def save_trip_to_db(user_id, token, destination, itinerary_text):
    if not FIREBASE_DB_URL or FIREBASE_DB_URL == "PASTE_FIREBASE_DATABASE_URL": return
    db_url = FIREBASE_DB_URL if FIREBASE_DB_URL.endswith('/') else FIREBASE_DB_URL + '/'
    url = f"{db_url}users/{user_id}/trips.json?auth={token}"
    requests.post(url, json={"destination": destination, "itinerary": itinerary_text, "timestamp": time.time()})

def get_user_trips(user_id, token):
    if not FIREBASE_DB_URL or FIREBASE_DB_URL == "PASTE_FIREBASE_DATABASE_URL": return {}
    db_url = FIREBASE_DB_URL if FIREBASE_DB_URL.endswith('/') else FIREBASE_DB_URL + '/'
    url = f"{db_url}users/{user_id}/trips.json?auth={token}"
    res = requests.get(url)
    return res.json() if res.status_code == 200 and res.json() else {}

# --- 6. ORIGINAL LOGIC HELPER FUNCTIONS ---
def get_ai_icon(text):
    t = text.lower()
    if "itinerary" in t or "day 1" in t or "blueprint" in t: return ":material/description:" 
    if "destination" in t or "where" in t or "city" in t: return ":material/pin_drop:" 
    if "budget" in t or "cost" in t or "inr" in t: return ":material/payments:" 
    if "welcome" in t or "hello" in t: return ":material/waving_hand:" 
    return ":material/support_agent:" 

def extract_first_name(email):
    raw_name = email.split('@')[0]
    clean_name = re.sub(r'[\.\_\-]', ' ', raw_name) 
    clean_name = re.sub(r'\d+', '', clean_name) 
    first_name = clean_name.split()[0].capitalize() if clean_name.split() else "Explorer"
    return first_name

def get_live_flights(origin, dest, out_date, ret_date):
    if not SERPAPI_KEY or SERPAPI_KEY == "PASTE_SERP_KEY_HERE": 
        return "### Live Flight Data\n*Error: SerpApi Key missing.*\n\n---\n\n"
    url = "https://serpapi.com/search.json"
    params = {"engine": "google_flights", "departure_id": origin, "arrival_id": dest, "outbound_date": out_date, "return_date": ret_date, "currency": "INR", "hl": "en", "type": "1", "api_key": SERPAPI_KEY}
    try:
        res = requests.get(url, params=params).json()
        if "best_flights" in res and len(res["best_flights"]) > 0:
            flight = res["best_flights"][0]
            price = flight.get("price", "Unknown")
            outbound = flight.get("flights", [{}])[0]
            out_airline = outbound.get("airline", "Unknown Airline")
            out_dep = outbound.get("departure_airport", {}).get("time", "Unknown Time")
            out_arr = outbound.get("arrival_airport", {}).get("time", "Unknown Time")
            
            output = f"### Live Round-Trip Flight Itinerary\n**Total Price:** INR {price} (Round-Trip per person)\n\n"
            output += f"**Outbound Flight ({out_date}):**\n- Airline: {out_airline}\n- Departure: {out_dep[:16] if isinstance(out_dep, str) else out_dep}\n- Arrival: {out_arr[:16] if isinstance(out_arr, str) else out_arr}\n\n"
            
            if len(flight.get("flights", [])) > 1:
                ret_flight = flight.get("flights", [])[-1]
                output += f"**Return Flight ({ret_date}):**\n- Airline: {ret_flight.get('airline', out_airline)}\n- Departure: {ret_flight.get('departure_airport', {}).get('time', 'Unknown Time')[:16]}\n- Arrival: {ret_flight.get('arrival_airport', {}).get('time', 'Unknown Time')[:16]}\n\n"
            else:
                output += f"**Return Flight ({ret_date}):**\n- Matches outbound airline.\n\n"
            output += "---\n\n"
            return output
        return f"### Live Flight Data\n*No direct live pricing found for {out_date} to {ret_date}.*\n\n---\n\n"
    except Exception:
        return ""

def create_pdf(text_content):
    class PDF(FPDF):
        def header(self):
            if os.path.exists(LOGO_FILE):
                self.image(LOGO_FILE, x=35, y=120, w=140)
                
    pdf = PDF()
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
        if not line: pdf.ln(3); continue
        if line.startswith('### '):
            pdf.ln(5); pdf.set_font("Arial", 'B', 15); pdf.multi_cell(0, 8, txt=line.replace('### ', '')); pdf.ln(2)
        elif line.startswith('**') and line.endswith('**'):
            pdf.set_font("Arial", 'B', 12); pdf.multi_cell(0, 7, txt=line.replace('**', ''))
        elif line.startswith('* **') or line.startswith('- **'):
            pdf.set_font("Arial", 'B', 11); pdf.multi_cell(0, 6, txt=line.replace('**', '').replace('* ', '- '))
        else:
            pdf.set_font("Arial", '', 11); pdf.multi_cell(0, 6, txt=line.replace('**', '').replace('*', '-'))
    return pdf.output(dest="S").encode("latin-1")

# --- 7. SESSION STATE INITIALIZATION ---
if "user" not in st.session_state: st.session_state.user = None
if "auth_mode" not in st.session_state: st.session_state.auth_mode = "login"
if "messages" not in st.session_state: st.session_state.messages = []
if "pending_prompt" not in st.session_state: st.session_state.pending_prompt = None
if "itinerary_generated" not in st.session_state: st.session_state.itinerary_generated = False

# THE NEW DEEP INTERVIEW SYSTEM PROMPT
SYSTEM_PROMPT = """
You are GenYatra, an elite, highly interactive AI Travel Architect. 
Your job is to act as a consultative travel agent. 
CRITICAL RULE: DO NOT generate the final day-by-day itinerary immediately. You MUST interview the user first.

PHASE 1: THE INTERVIEW (Interactive)
Ask the user step-by-step questions to build their perfect trip. Ask 1 or 2 questions at a time. Wait for their reply.
You MUST gather the following information before generating the trip:
1. Exact Destination(s).
2. Mode of Transport (Train, Flight, Bus, Personal Car). DO NOT assume they want a flight.
3. Duration of the trip and preferred month/dates.
4. Who is traveling (Solo, couple, family, friends).
5. Approximate Budget (Luxury, Mid-range, Budget).
6. Specific locations or activities they want to experience.
7. Lodging preferences (Resort, Homestay, Hostel, etc.).

PHASE 2: THE MASTER ITINERARY
Once, and ONLY once, you have all the information, tell them you are finalizing the itinerary.
- Provide a day-by-day breakdown.
- HOTEL LOGIC: Provide real, specific hotel names based on their preference.
- RESTAURANTS: Name REAL, specific restaurants for meals.
- NEVER use markdown tables. Use standard bullet points.

SYSTEM TAGS:
- If they explicitly choose flights, output: [FLIGHT_SEARCH: ORIGIN_IATA, DEST_IATA, YYYY-MM-DD, YYYY-MM-DD]
- Output [PDF_READY] at the very bottom of your response ONLY when you are outputting the final day-by-day itinerary. Never output this during the interview phase.
"""

# --- SDK INITIALIZATION ---
chat_session = None
if GEMINI_KEY and GEMINI_KEY != "PASTE_YOUR_GEMINI_KEY_HERE":
    try:
        formatted_history = []
        for msg in st.session_state.messages:
            role = "model" if msg["role"] == "assistant" else "user"
            formatted_history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))
            
        client = genai.Client(api_key=GEMINI_KEY)
        chat_session = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            history=formatted_history
        )
    except Exception:
        pass

# --- 8. THE MASTER LOGIC ENGINE ---
def run_architect_engine(prompt):
    if not chat_session:
        st.error("🚨 System Error: Gemini API Key is missing or invalid.")
        st.stop()
        
    with st.chat_message("assistant", avatar=":material/psychology:"):
        with st.status("Processing...", expanded=True) as status:
            time.sleep(1) 
            try:
                status.update(label="Analyzing your travel preferences...", state="running")
                response = chat_session.send_message(prompt)
                clean_text = response.text
                live_flight_text = ""
                show_pdf_button = False
                
                clean_text = re.sub(r'\[.*?_SEARCH:\s*[^\]]+\]', '', clean_text, flags=re.IGNORECASE).strip()

                flight_match = re.search(r'\[FLIGHT_SEARCH:\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^\]]+)\]', response.text, re.IGNORECASE)
                if flight_match:
                    status.update(label="Searching live flight fares & timings...", state="running")
                    origin, dest, out_date, ret_date = flight_match.groups()
                    live_flight_text = get_live_flights(origin.strip(), dest.strip(), out_date.strip(), ret_date.strip())

                if "[PDF_READY]" in clean_text:
                    show_pdf_button = True
                    st.session_state.itinerary_generated = True 
                    clean_text = clean_text.replace("[PDF_READY]", "").strip()

                final_output = live_flight_text + clean_text
                status.update(label="Complete.", state="complete", expanded=False)
                
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
            st.session_state.last_generated_itinerary = final_output
            st.session_state.show_pdf_button = True
            
        st.rerun()


# --- 9. MAIN APPLICATION ROUTING ---

if not st.session_state.user:
    st.write("<br>", unsafe_allow_html=True)
    _, col_center, _ = st.columns([1, 1.2, 1]) 
    
    with col_center:
        st.markdown("<div class='login-btn-container anim-1'>", unsafe_allow_html=True)
        
        st.markdown("<div class='brand-container'><p class='welcome-to'>welcome to</p></div>", unsafe_allow_html=True)
        if encoded_logo:
            st.markdown(f"<img src='data:image/jpeg;base64,{encoded_logo}' alt='GenYatra Logo' class='login-logo'>", unsafe_allow_html=True)
        else:
            st.markdown("<h1 style='text-align: center; color: #1A73E8;'>GenYatra</h1>", unsafe_allow_html=True)
            
        if st.session_state.auth_mode == "login":
            st.markdown("<div class='auth-header-professional'>Welcome Back</div>", unsafe_allow_html=True)
            st.markdown("<div class='auth-subtitle'>Log in to your dashboard to continue.</div>", unsafe_allow_html=True)
            with st.container():
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_pass")
                st.write("")
                if st.button("Login", type="primary", use_container_width=True):
                    if FIREBASE_API_KEY == "PASTE_FIREBASE_WEB_API_KEY" or not FIREBASE_API_KEY:
                        st.error("Missing Firebase Key in code.")
                    else:
                        res = sign_in(email, password)
                        if "error" in res: st.error("Invalid credentials.")
                        else:
                            st.session_state.user = {"email": email, "idToken": res["idToken"], "localId": res["localId"], "is_guest": False}
                            st.rerun()
            st.markdown("<div class='divider'>OR</div>", unsafe_allow_html=True)
            if st.button("Don't have an account? Sign Up", use_container_width=True):
                st.session_state.auth_mode = "signup"
                st.rerun()
            if st.button("Continue as Guest", use_container_width=True):
                st.session_state.user = {"email": "Explorer Explorer", "is_guest": True}
                st.rerun()
        else:
            st.markdown("<div class='auth-header-professional'>Create Account</div>", unsafe_allow_html=True)
            st.markdown("<div class='auth-subtitle'>Join GenYatra to save your custom itineraries.</div>", unsafe_allow_html=True)
            with st.container():
                email = st.text_input("Email", key="signup_email")
                password = st.text_input("Password", type="password", key="signup_pass")
                st.write("")
                if st.button("Sign Up", type="primary", use_container_width=True):
                    if FIREBASE_API_KEY == "PASTE_FIREBASE_WEB_API_KEY" or not FIREBASE_API_KEY:
                        st.error("Missing Firebase Key in code.")
                    else:
                        res = sign_up(email, password)
                        if "error" in res: st.error(res["error"]["message"])
                        else: 
                            st.success("Account created! Logging you in...")
                            time.sleep(1)
                            st.session_state.auth_mode = "login"
                            st.rerun()
            st.markdown("<div class='divider'>OR</div>", unsafe_allow_html=True)
            if st.button("Already have an account? Login", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.rerun()
            if st.button("Continue as Guest", use_container_width=True):
                st.session_state.user = {"email": "Explorer Explorer", "is_guest": True}
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

else:
    with st.sidebar:
        # Sidebar Logo
        if encoded_logo:
             st.markdown(f"<img src='data:image/jpeg;base64,{encoded_logo}' style='max-width: 150px; margin-bottom: 25px; display: block;'>", unsafe_allow_html=True)
        else:
            st.markdown("<h2 style='font-weight: 900; margin-bottom: 25px;'>GenYatra</h2>", unsafe_allow_html=True)
            
        # Custom Premium Profile Badge HTML
        display_name = "Explorer" if st.session_state.user.get("is_guest") else extract_first_name(st.session_state.user['email'])
        initial = display_name[0].upper() if display_name else "E"
        
        st.markdown(f"""
            <div class="profile-badge">
                <div class="profile-avatar">{initial}</div>
                <div>
                    <div style="font-weight: 600; font-size: 0.95rem;">{display_name}</div>
                    <div style="font-size: 0.75rem; opacity: 0.7;">GenYatra Member</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("") # spacing
        
        if st.button("➕ Start New Trip", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending_prompt = None
            st.session_state.itinerary_generated = False
            st.rerun()
            
        if st.button("🔓 Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.messages = []
            st.session_state.pending_prompt = None
            st.session_state.itinerary_generated = False
            st.session_state.auth_mode = "login"
            st.rerun()
            
        st.markdown("<br><hr style='opacity: 0.2;'><br>", unsafe_allow_html=True)
        st.markdown("<div style='font-weight: 600; margin-bottom: 10px;'>Saved Trips</div>", unsafe_allow_html=True)
        
        if st.session_state.user.get("is_guest"):
            st.caption("Guest Mode: History disabled.")
        else:
            history = get_user_trips(st.session_state.user["localId"], st.session_state.user["idToken"])
            if history:
                for trip_id, trip_data in history.items():
                    with st.expander(f"📍 {trip_data.get('destination', 'Trip')}"):
                        st.write(trip_data.get("itinerary", "")[:100] + "...")
            else:
                st.caption("No trips saved yet.")

    _, main_ui_col, _ = st.columns([0.5, 3.0, 0.5])
    
    with main_ui_col:
        
        if not st.session_state.messages and not st.session_state.pending_prompt:
            st.write("<br><br><br><br>", unsafe_allow_html=True)
            
            clean_first_name = "Explorer" if st.session_state.user.get("is_guest") else extract_first_name(st.session_state.user['email'])
            
            st.markdown(f"<div class='gemini-greeting anim-1'>Hi, {clean_first_name}!!</div>", unsafe_allow_html=True)
            st.markdown("<div class='gemini-greeting-sub anim-2'>I'm ready to help you plan, explore, and travel.</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='anim-3'>", unsafe_allow_html=True)
            with st.form("initial_search", clear_on_submit=True, border=False):
                search_col, btn_col = st.columns([6, 1])
                with search_col:
                    first_input = st.text_input("Search", placeholder="Ask GenYatra to plan your trip...", label_visibility="collapsed")
                with btn_col:
                    submit_search = st.form_submit_button("Plan")
                
                if submit_search and first_input:
                    st.session_state.messages.append({"role": "user", "content": first_input, "icon": ":material/person:"})
                    st.session_state.pending_prompt = first_input
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        else:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f"""
                        <div style='display: flex; justify-content: flex-end; margin-bottom: 20px;'>
                            <div style='max-width: 80%; padding: 12px 18px; border-radius: 12px; background-color: rgba(128,128,128,0.1); color: inherit; font-size: 1rem;'>
                                {msg["content"]}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    col_icon, col_txt = st.columns([1, 15])
                    with col_icon: st.write(msg.get("icon", ":material/psychology:"))
                    with col_txt: st.markdown(msg["content"])
            
            if st.session_state.pending_prompt:
                prompt_to_run = st.session_state.pending_prompt
                st.session_state.pending_prompt = None 
                run_architect_engine(prompt_to_run)
            
            if st.session_state.itinerary_generated and hasattr(st.session_state, 'last_generated_itinerary'):
                st.markdown("---")
                st.subheader("Your Master Itinerary")
                tab_overview, tab_itinerary, tab_budget = st.tabs(["Overview", "Day-by-Day", "Budget & PDF"])
                
                with tab_overview:
                    st.markdown("### Destination Overview")
                    st.markdown(st.session_state.last_generated_itinerary.split("Day 1")[0][:500] if "Day 1" in st.session_state.last_generated_itinerary else st.session_state.last_generated_itinerary[:500])
                with tab_itinerary:
                    st.markdown(st.session_state.last_generated_itinerary)
                with tab_budget:
                    st.success("Your itinerary is ready to download.")
                    if st.session_state.show_pdf_button:
                        pdf_bytes = create_pdf(st.session_state.last_generated_itinerary)
                        st.download_button("Download Master Itinerary (PDF)", data=pdf_bytes, file_name="GenYatra_Itinerary.pdf", mime="application/pdf")
                        if not st.session_state.user.get("is_guest"):
                            first_prompt = st.session_state.messages[0]["content"] if st.session_state.messages else "New Trip"
                            save_trip_to_db(st.session_state.user["localId"], st.session_state.user["idToken"], first_prompt[:30] + "...", st.session_state.last_generated_itinerary)
            
            user_input = st.chat_input("Reply to the architect...")
            if user_input:
                st.session_state.messages.append({"role": "user", "content": user_input, "icon": ":material/person:"})
                st.markdown(f"""
                        <div style='display: flex; justify-content: flex-end; margin-bottom: 20px;'>
                            <div style='max-width: 80%; padding: 12px 18px; border-radius: 12px; background-color: rgba(128,128,128,0.1); color: inherit; font-size: 1rem;'>
                                {user_input}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                run_architect_engine(user_input)
