
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
import os

from src.core.profile_manager import ProfileManager  # Fixed path
from src.core.keyword_search import KeywordSearchEngine
from src.agents.simple_extractor import SimpleExtractor
from src.agents.context_aware_sales import ContextAwareSalesAgent
from src.agents.orchestrator import OrchestratorAgent

# --- Setup ---
load_dotenv()
st.set_page_config(page_title="AI Real Estate Agent V4 (RAG)", layout="wide")

if not os.getenv("GOOGLE_API_KEY"):
    st.error("Please set GOOGLE_API_KEY in .env")
    st.stop()

# Initialize Components
if 'components_initialized' not in st.session_state:
    st.session_state.components = {
        "profile_mgr": ProfileManager(),
        "search_engine": KeywordSearchEngine(),  # NEW: Simple keyword search
        "orchestrator": OrchestratorAgent(),
        "extractor": SimpleExtractor(),  # NEW: Simple extraction
        "sales": ContextAwareSalesAgent()
    }
    st.session_state.components_initialized = True

comps = st.session_state.components

# --- UI Styling & Animations ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global Reset & Typography */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        font-feature-settings: "cv02", "cv03", "cv04", "cv11";
        -webkit-font-smoothing: antialiased;
    }

    /* Professional Dark Theme (Vercel/Apple Style) */
    .stApp {
        background-color: #000000;
        color: #ededed;
    }

    /* Remove Streamlit branding/padding quirks */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        max-width: 1000px;
    }
    
    header { visibility: hidden; }
    footer { visibility: hidden; }

    /* --- Chat Bubbles --- */
    /* User Message - Blue/Modern */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: transparent;
    }
    
    div[data-testid="chatAvatarIcon-user"] {
        background-color: #007AFF !important;
        color: white !important;
    }
    
    /* Assistant Message - Clean/Dark */
    div[data-testid="chatAvatarIcon-assistant"] {
        background-color: #1c1c1e !important;
        color: #a1a1aa !important;
    }

    /* Message Content Container */
    [data-testid="stChatMessageContent"] {
        border-radius: 12px;
        padding: 12px 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Specific User Bubble Style (Targeting user role via CSS if possible, else generic) */
    /* Note: Streamlit doesn't expose role class on the container easily, relying on JS usually.
       We'll style the generics clean. */
       
    [data-testid="stChatMessageContent"] {
        background: #111111;
    }

    /* --- Property Cards (Minimalist) --- */
    .property-card {
        background: #09090b; 
        border: 1px solid #18181b; 
        border-radius: 8px; /* Sharper corners */
        padding: 16px;
        transition: all 0.2s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        position: relative;
    }

    .property-card:hover {
        border-color: #3f3f46; 
        background: #101012;
    }

    .card-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #ffff;
        margin-bottom: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .card-dev {
        font-size: 0.75rem;
        color: #71717a;
        margin-bottom: 12px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* --- Ghost Button (View Details) --- */
    .stButton button {
        background: transparent;
        color: #a1a1aa;
        border: 1px solid #27272a;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 0.8rem;
        font-weight: 500;
        transition: all 0.1s;
        box-shadow: none;
        width: 100%;
    }
    
    .stButton button:hover {
        background: #ffffff;
        color: #000000;
        border-color: #ffffff;
        transform: none; /* remove scale */
        box-shadow: 0 4px 12px rgba(255,255,255,0.1);
    }
    
    /* Active Card Highlight */
    .property-card.active {
        border-color: #fff;
        background: #101012;
    }

    /* Hero Text */
    .hero-title {
        font-size: 2rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
        text-align: left;
    }
    
    .hero-subtitle {
        font-size: 1rem;
        color: #71717a;
        font-weight: 400;
        text-align: left;
        margin-bottom: 2rem;
    }

    /* Right Panel Styling */
    .right-panel {
        background: #09090b;
        border-left: 1px solid #27272a;
        height: 100vh;
        padding: 20px;
        position: fixed; 
        right: 0; 
        top: 0;
        overflow-y: auto;
    }

</style>
""", unsafe_allow_html=True)

# --- Logic: Detail Panel ---
def render_details_panel(row):
    """Renders the details in the right column"""
    with st.container(border=True):
        c1, c2 = st.columns([0.85, 0.15])
        with c1:
            st.markdown(f"### {row.get('Project Name', 'N/A')}")
            st.caption(f"by {row.get('Developer', 'Unknown')}")
        with c2:
            if st.button("✕", key="close_details"):
                st.session_state.selected_property = None
                st.rerun()

        st.divider()

        # Tabs for details
        t1, t2, t3, t4 = st.tabs(["Overview", "Specs", "Finance", "ROI Tool"])
        
        with t1:
            st.markdown(f"**📍 Location:** {row.get('Location', '-')}")
            st.markdown(f"**🏙️ Region:** {row.get('Region', '-')}")
            st.markdown(f"**🏗️ Status:** {row.get('Project Status', '-')}")
            st.markdown("---")
            st.info(f"**Amenities:** {row.get('Key Amenities', 'N/A')}")

        with t2:
            st.caption("Key Specifications")
            # Safe filtering for specs
            specs = {}
            for k, v in row.items():
                if k in ['search_blob', 'price_numeric', 'parsed_price']:
                    continue
                
                # Safe check
                is_valid = False
                if isinstance(v, (list, tuple, np.ndarray)):
                    is_valid = len(v) > 0
                else:
                    is_valid = pd.notna(v)
                
                if is_valid:
                    specs[k] = v

            # Display important specs first
            cols = ['Project Type', 'Total Units', 'Total Land Area (Acres)']
            for c in cols:
                if c in specs:
                    st.markdown(f"**{c}:** {specs[c]}")
            
            with st.expander("See All Data"):
                st.json(str(specs)) # Simple dump for now or formatted list

        with t3:
            # Handle Price Parsing Safely
            raw_price = row.get('Price per sqft (Enriched)', 0)
            price = 0
            try:
                if isinstance(raw_price, (int, float)):
                    price = raw_price
                elif isinstance(raw_price, str):
                    # Robust cleaning: Remove currency, commas, tildes, approx symbols
                    clean_price = raw_price.replace('₹', '').replace(',', '').replace('~', '').strip()
                    
                    # Handle ranges like "4500 - 5000" (Take the lower bound for conservative estimates)
                    if '-' in clean_price:
                        clean_price = clean_price.split('-')[0].strip()
                        
                    # Handle "On Request" or text
                    if clean_price.replace('.', '', 1).isdigit():
                        price = float(clean_price)
            except:
                price = 0

            st.metric("Price/SqFt", f"₹{price}")
            
            if price > 0:
                st.markdown("#### Estimated Cost")
                st.write(f"1200 sqft: **₹{(price * 1200 / 10000000):.2f} Cr**")
                st.write(f"1500 sqft: **₹{(price * 1500 / 10000000):.2f} Cr**")
            else:
                st.warning("Price data unavailable for calculation.")

        with t4:
            st.write("#### 📈 Investment Projector")
            appr = st.slider("Annual Growth %", 5, 20, 8, key=f"roi_slider_{row.get('Project Name')}")
            yrs = st.slider("Years", 1, 10, 5, key=f"roi_years_{row.get('Project Name')}")
            
            if price > 0:
                initial = price * 1500 # Base 1500 sqft
                final = initial * ((1 + appr/100) ** yrs)
                profit = final - initial
                
                st.success(f"Proj. Profit: **₹{profit/100000:.1f} Lakhs**")
                
                # Simple Chart
                chart_data = pd.DataFrame({
                    "Year": [f"Year {i}" for i in range(yrs + 1)],
                    "Value": [initial * ((1 + appr/100) ** i) for i in range(yrs + 1)]
                })
                st.line_chart(chart_data.set_index("Year"))

# --- User Session ---
if 'user_id' not in st.session_state:
    st.session_state.user_id = "user_001"
    st.session_state.messages = []
if 'selected_property' not in st.session_state:
    st.session_state.selected_property = None

user = comps["profile_mgr"].get_or_create_user(st.session_state.user_id, "Client")
active_funnel = comps["profile_mgr"].get_active_funnel(st.session_state.user_id)

# --- Sidebar ---
st.sidebar.markdown("### 📊 Search Status")
st.sidebar.caption(f"Funnel: {active_funnel['name']}")
if st.sidebar.button("Start New Search", type="secondary"):
    new_f = comps["profile_mgr"].create_funnel(st.session_state.user_id, "New Search")
    st.session_state.selected_property = None
    st.rerun()

st.sidebar.divider()
transcript_path = "data/transcripts.log"
if os.path.exists(transcript_path):
    st.sidebar.caption("🎙️ Live Transcript")
    with open(transcript_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines[-5:]:
            st.sidebar.text(line.strip())
    if st.sidebar.button("Clear Log"):
        os.remove(transcript_path)
        st.rerun()

# --- Main Layout (Persistent Master-Detail) ---

# Always create 2 columns to maintain layout stability
# 65% Chat (Left), 35% Details (Right)
main_col, details_col = st.columns([0.65, 0.35], gap="small")

with main_col:
    st.markdown('<div class="hero-title">AI Real Estate Consultant</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Intelligent property search for Bangalore</div>', unsafe_allow_html=True)

    # Chat Loop
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # Render Cards Inline
            if "cards" in msg and msg['cards']:
                matches_df = pd.DataFrame(msg["cards"])
                if not matches_df.empty:
                    # Always 2 columns for cards since we are in 65% width
                    cols = st.columns(2)
                    
                    for idx, (_, row) in enumerate(matches_df.head(6).iterrows()):
                        with cols[idx % 2]:
                            # Card HTML
                            st.markdown(f"""
                            <div class="property-card">
                                <div>
                                     <div class="card-title">{row.get('Project Name', 'N/A')}</div>
                                     <div class="card-dev">{row.get('Developer', 'Unknown')}</div>
                                     <div style="color: #9ca3af; font-size: 0.8rem;">📍 {str(row.get('Location', 'N/A'))[:20]}</div>
                                     <div style="color: #e2e8f0; font-weight: 500; font-size: 0.9rem; margin-top: 4px;">₹{row.get('Price per sqft (Enriched)', 'Ask')}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Selection Logic
                            def select_prop(r=row):
                                st.session_state.selected_property = r.to_dict()
                            
                            st.button("View Details", key=f"btn_{idx}_{len(msg['content'])}", on_click=select_prop)


    if prompt := st.chat_input("Ask about properties..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Processing..."):
            # Orchestration -> Extraction -> Search -> Sales
            decision = comps["orchestrator"].decide_action(prompt, active_funnel)
            if decision.get("action") == "NEW":
                active_funnel = comps["profile_mgr"].create_funnel(st.session_state.user_id, "New Search")
                active_funnel['criteria'] = {} # Reset
            
            new_criteria = comps["extractor"].extract(prompt)
            comps["profile_mgr"].update_funnel_criteria(st.session_state.user_id, active_funnel['id'], new_criteria)
            
            matches = comps["search_engine"].search(active_funnel['criteria'])
            response_text = comps["sales"].generate_response(active_funnel['criteria'], matches, prompt)

        msg_data = {"role": "assistant", "content": response_text}
        if not matches.empty:
            msg_data["cards"] = matches.head(12).to_dict('records')
        
        st.session_state.messages.append(msg_data)
        st.rerun()

# --- Render Details Panel (Always in Right Column) ---
with details_col:
    if st.session_state.selected_property:
        render_details_panel(st.session_state.selected_property)
    else:
        # Empty State
        st.markdown("""
        <div style='
            height: 80vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            color: #3f3f46; 
            text-align: center;
            border: 1px dashed #27272a;
            border-radius: 12px;
        '>
            <div>
                <div style='font-size: 2rem; margin-bottom: 10px;'>👈</div>
                <div>Select a property<br>to view details</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
