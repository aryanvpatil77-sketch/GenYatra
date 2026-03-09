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
st.set_page_config(page_title="GenYatra | AI Travel Architect", layout="wide", initial_sidebar_state="expanded")

# --- 2. DEPLOYMENT API KEYS ---
SERPAPI_KEY = st.secrets.get("SERPAPI_KEY", "")
GEMINI_KEY = st.secrets.get("GEMINI_KEY", st.secrets.get("GEMINI_API_KEY", "")) 
FIREBASE_API_KEY = st.secrets.get("FIREBASE_API_KEY", "")
FIREBASE_DB_URL = st.secrets.get("FIREBASE_DB_URL", "")

# --- 3. PREMIUM THEME-AGNOSTIC CSS ---
st.markdown("""
    <style>
    /* Hide Streamlit Clutter */
    #MainMenu, footer, header, [data-testid="stDecoration"] { display: none !important; }
    
    /* Native Dark/Light Mode Adaptability */
    [data-testid="stAppViewContainer"], main, [data-testid="stBottomBlock"], [data-testid="stBottom"] { 
        background: transparent !important; background-color: transparent !important; 
    }
    
    /* Pull the app up to remove the massive default top spacing */
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* Kill the annoying "Press Enter to apply" text */
    [data-testid="InputInstructions"] { display: none !important; }
    
    /* Typography & Branding (Tightened for single-screen view) */
    .brand-container { text-align: center; margin-top: 0vh; margin-bottom: 15px; }
    .welcome-to { color: #FF9933 !important; font-size: 1rem; font-weight: 600; letter-spacing: 2px; text-transform: lowercase; margin: 0; }
    .genyatra-title { font-size: 3.2rem; font-weight: 900; letter-spacing: -1.5px; margin-top: -5px; margin-bottom: 0px; }
    
    .auth-header { text-align: center; font-size: 1.5rem; font-weight: 700; margin-bottom: 10px; }
    .divider { text-align: center; color: rgba(128,128,128,0.5); margin: 15px 0; font-size: 0.8rem; font-weight: 600; letter-spacing: 1px; }

    /* Remove default Streamlit form box outline to keep UI clean */
    [data-testid="stForm"] { border: none !important; padding: 0px !important; background-color: transparent !important; box-shadow: none !important; }

    /* Custom Auth Buttons (Slimmer margins) */
    .login-btn-container [data-testid="baseButton-primary"] {
        background-color: #1A73E8 !important; color: #FFFFFF !important; border-radius: 8px !important;
        padding: 8px 24px !important; border: none !important; font-weight: 600 !important; margin-top: 5px !important;
    }
    .login-btn-container [data-testid="baseButton-secondary"] {
        background-color: transparent !important; border-radius: 8px !important; border: 1px solid rgba(128,128,128,0.3) !important;
        padding: 8px 24px !important; font-weight: 500 !important; margin-top: 5px !important;
    }
    
    /* Gemini Dynamic Home Screen Typography */
    .gemini-greeting { 
        font-size: 3.5rem; font-weight: 500; 
        background: -webkit-linear-gradient(45deg, #1A73E8, #E94235); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
        margin-bottom: 0px; text-align: left;
    }
    .gemini-greeting-sub { 
        font-size: 3.5rem; color: rgba(128,128,128,0.8); font-weight: 400; 
        margin-top: 0px; margin-bottom: 40px; text-align: left;
    }
    
    /* Full Width Chat Bubbles */
    [data-testid="stChatMessage"] { 
        background-color: rgba(128, 128, 128, 0.03) !important; 
        border-radius: 8px; padding: 20px; 
        border: 1px solid rgba(128, 128, 128, 0.15); margin-bottom: 16px; 
    }
    </style>
""", unsafe_allow_html=True)

# --- 4. FIREBASE LOGIC ---
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

# --- 5. ORIGINAL LOGIC HELPER FUNCTIONS ---
def get_ai_icon(text):
    t = text.lower()
    if "itinerary" in t or "day 1" in t or "blueprint" in t: return ":material/description:" 
    if "destination" in t or "where" in t or "city" in t: return ":material/pin_drop:" 
    if "budget" in t or "cost" in t or "inr" in t: return ":material/payments:" 
    if "welcome" in t or "hello" in t: return ":material/waving_hand:" 
    return ":material/support_agent:" 

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

# --- 6. SESSION STATE INITIALIZATION ---
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

# --- 7. THE MASTER LOGIC ENGINE ---
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
                
                # Strip out any random System Tags (like [TRAIN_SEARCH...]) so they don't bleed into the UI
                clean_text = re.sub(r'\[.*?_SEARCH:\s*[^\]]+\]', '', clean_text, flags=re.IGNORECASE).strip()

                # Handle Flight Search specifically if it exists
                flight_match = re.search(r'\[FLIGHT_SEARCH:\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^\]]+)\]', response.text, re.IGNORECASE)
                if flight_match:
                    status.update(label="Searching live flight fares & timings...", state="running")
                    origin, dest, out_date, ret_date = flight_match.groups()
                    live_flight_text = get_live_flights(origin.strip(), dest.strip(), out_date.strip(), ret_date.strip())

                # Unlock the final UI Tabs only when PDF_READY is triggered
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
        
        # Original Streaming Logic
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


# --- 8. MAIN APPLICATION ROUTING ---

# ROUTE A: LOGIN SCREEN
if not st.session_state.user:
    st.markdown("<div class='brand-container'><p class='welcome-to'>welcome to</p><h1 class='genyatra-title'>GenYatra</h1></div>", unsafe_allow_html=True)
    _, col_center, _ = st.columns([1, 1.2, 1]) 
    
    with col_center:
        st.markdown("<div class='login-btn-container'>", unsafe_allow_html=True)
        if st.session_state.auth_mode == "login":
            st.markdown("<div class='auth-header'>Welcome Back</div>", unsafe_allow_html=True)
            with st.container():
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                st.write("")
                if st.button("Sign In", type="primary", use_container_width=True):
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
                st.session_state.user = {"email": "Guest Explorer", "is_guest": True}
                st.rerun()
        else:
            st.markdown("<div class='auth-header'>Create your Account</div>", unsafe_allow_html=True)
            with st.container():
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
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
            if st.button("Already have an account? Log In", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.rerun()
            if st.button("Continue as Guest", use_container_width=True):
                st.session_state.user = {"email": "Guest Explorer", "is_guest": True}
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ROUTE B: SECURE DASHBOARD
else:
    # Sidebar
    with st.sidebar:
        st.markdown("<h2 style='font-weight: 900; letter-spacing: -1px; margin-bottom: 0px;'>GenYatra</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #FF9933; font-size: 0.7rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; margin-top: 0px; margin-bottom: 30px;'>AI Architect</p>", unsafe_allow_html=True)
        
        display_name = st.session_state.user['email'].split('@')[0].capitalize() if not st.session_state.user.get("is_guest") else "Guest"
        st.caption(f"Profile: {display_name}")
        
        if st.button("Start New Trip", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending_prompt = None
            st.session_state.itinerary_generated = False
            st.rerun()
            
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.messages = []
            st.session_state.pending_prompt = None
            st.session_state.itinerary_generated = False
            st.session_state.auth_mode = "login"
            st.rerun()
            
        st.divider()
        st.subheader("Saved Trips")
        if st.session_state.user.get("is_guest"):
            st.caption("Guest Mode: History disabled.")
        else:
            history = get_user_trips(st.session_state.user["localId"], st.session_state.user["idToken"])
            if history:
                for trip_id, trip_data in history.items():
                    with st.expander(trip_data.get("destination", "Trip")):
                        st.write(trip_data.get("itinerary", "")[:100] + "...")
            else:
                st.caption("No trips saved yet.")


    # --- FULL SCREEN DYNAMIC LAYOUT ---
    
    # Use a single, wide column for the main interface
    _, main_ui_col, _ = st.columns([0.5, 3.0, 0.5])
    
    with main_ui_col:
        
        # STATE 1: GEMINI HOME SCREEN (No messages yet)
        if not st.session_state.messages and not st.session_state.pending_prompt:
            st.write("<br><br><br><br>", unsafe_allow_html=True)
            user_name = st.session_state.user['email'].split('@')[0].capitalize() if not st.session_state.user.get("is_guest") else "Explorer"
            st.markdown(f"<div class='gemini-greeting'>Hi {user_name}</div>", unsafe_allow_html=True)
            st.markdown("<div class='gemini-greeting-sub'>Where should we start?</div>", unsafe_allow_html=True)
            
            with st.form("initial_search", clear_on_submit=True, border=False):
                search_col, btn_col = st.columns([6, 1])
                with search_col:
                    first_input = st.text_input("Search", placeholder="Ask GenYatra to plan your trip...", label_visibility="collapsed")
                with btn_col:
                    submit_search = st.form_submit_button("Plan", use_container_width=True)
                
                if submit_search and first_input:
                    st.session_state.messages.append({"role": "user", "content": first_input, "icon": ":material/person:"})
                    st.session_state.pending_prompt = first_input
                    st.rerun()

        # STATE 2 & 3: CHAT & INTERVIEW MODE (Full Screen)
        else:
            # 1. Render all history
            for msg in st.session_state.messages:
                icon = msg.get("icon", ":material/person:") if msg["role"] == "assistant" else ":material/person:"
                with st.chat_message(msg["role"], avatar=icon):
                    st.markdown(msg["content"])
            
            # 2. Process Home Screen Handoff 
            if st.session_state.pending_prompt:
                prompt_to_run = st.session_state.pending_prompt
                st.session_state.pending_prompt = None 
                run_architect_engine(prompt_to_run)
            
            # 3. Render Tabs at the bottom ONLY if generated
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
            
            # 4. Chat Box (Always visible at the bottom)
            user_input = st.chat_input("Reply to the architect...")
            if user_input:
                st.session_state.messages.append({"role": "user", "content": user_input, "icon": ":material/person:"})
                with st.chat_message("user", avatar=":material/person:"):
                    st.markdown(user_input)
                run_architect_engine(user_input)
