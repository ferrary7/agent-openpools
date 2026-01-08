import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

# --- Page Config ---
st.set_page_config(page_title="AI Real Estate Agent", layout="wide")

# --- Setup Gemini ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("GOOGLE_API_KEY not found in .env file. Please add it.")
    st.stop()

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.warning("Please provide a Google API Key to proceed.")
    st.stop()

# --- Load Data ---
@st.cache_data
def load_data():
    try:
        df = pd.read_excel('banglore_pools.xlsx')
        # Normalize column names
        df.columns = [c.strip() for c in df.columns]
        
        # Helper to clean price
        def parse_price(val):
            if pd.isna(val): return 0
            s = str(val).lower().replace('₹', '').replace(',', '').strip()
            try:
                if 'cr' in s:
                    return float(s.replace('cr', '').strip()) * 10000000
                if 'l' in s or 'lac' in s:
                    return float(s.replace('l', '').replace('lac', '').strip()) * 100000
                
                # Handle ranges like "11000-13000"
                if '-' in s:
                    parts = s.split('-')
                    avg = sum(float(p.strip()) for p in parts) / len(parts)
                    return avg
                    
                return float(s)
            except:
                return 0
                
        # Create a numeric price column if possible, otherwise rely on AI reading text
        # Let's try to parse 'Price per sqft (Enriched)' if it exists, or just keep as is.
        # Based on previous inspection, we have 'Price per sqft (Enriched)'.
        if 'Price per sqft (Enriched)' in df.columns:
            df['price_numeric'] = df['Price per sqft (Enriched)'].apply(parse_price)
            
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

# --- Session State Management ---
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'user_preferences' not in st.session_state:
    st.session_state.user_preferences = {
        "location": None,
        "min_price": None,
        "max_price": None,
        "bhk": None,
        "amenities": []
    }

# --- Helper Functions ---

def clean_price(price_str):
    """Attempt to convert price string to float number."""
    if isinstance(price_str, (int, float)):
        return float(price_str)
    try:
        # Remove chars like '₹', ',', 'lac', 'cr' and convert
        # This is a basic cleaner, might need refinement based on data
        p = str(price_str).lower().replace(',', '').replace('₹', '')
        if 'cr' in p:
            return float(p.replace('cr', '').strip()) * 10000000
        if 'l' in p or 'lac' in p:
            return float(p.replace('l', '').replace('lac', '').strip()) * 100000
        return float(p)
    except:
        return 0

def search_properties(preferences, dataframe):
    if dataframe is None or dataframe.empty:
        return pd.DataFrame()
        
    filtered_df = dataframe.copy()
    
    # Filter by Location (Flexible Token Match)
    if preferences.get('location') and isinstance(preferences['location'], str):
        loc_term = preferences['location'].lower()
        # Split terms to allow "Electronic City" to match "Electronic City Phase 2"
        # but avoid very short common words if possible, though simple 'and' logic is usually better
        # Let's try: if the location string provided by user is a substring of the data.
        
        cols_to_search = [c for c in ['Location', 'Region', 'Address Map'] if c in filtered_df.columns]
        
        # Create a mask for any match
        mask = pd.Series(False, index=filtered_df.index)
        for col in cols_to_search:
            # We check if the user's location term is contained in the column
            mask |= filtered_df[col].astype(str).str.lower().str.contains(loc_term, na=False)
            
        filtered_df = filtered_df[mask]
        
    # Filter by Price (if parsed)
    if 'price_numeric' in filtered_df.columns:
        if preferences.get('min_price'):
            try:
                min_p = float(preferences['min_price'])
                filtered_df = filtered_df[filtered_df['price_numeric'] >= min_p]
            except: pass
            
        if preferences.get('max_price'):
            try:
                max_p = float(preferences['max_price'])
                filtered_df = filtered_df[filtered_df['price_numeric'] <= max_p]
            except: pass
            
    # Filter by Developer
    if preferences.get('developer'):
        dev = preferences['developer'].lower()
        if 'Developer' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Developer'].astype(str).str.lower().str.contains(dev, na=False)]
    
    # Return more results to ensure we fill the grid
    return filtered_df.head(20)

def extract_intent(user_input, current_prefs):
    """
    Uses Gemini to update the user preferences JSON.
    """
    prompt = f"""
    You are a smart data extraction assistant.
    Current User Preferences: {json.dumps(current_prefs)}
    User Input: "{user_input}"
    
    Task: 
    1. Update the 'Current User Preferences' based on the 'User Input'.
    2. Overwrite values if new information is provided.
    3. For 'location', extract the general area name (e.g. 'Whitefield', 'Electronic City') rather than full address.
    4. For prices, convert 'k', 'lakh', 'cr' to absolute numbers (e.g. '10k' -> 10000, '1.5cr' -> 15000000).
    5. Extract 'developer' if the user mentions a builder (e.g. 'Prestige', 'Brigade', 'Sobha').
    6. CRITICAL: If the user changes the topic (e.g. asks about a different location or developer completely), CLEAR the previous incompatible preferences (e.g. reset 'location' if asking about a specific builder whose projects might be elsewhere, or if they explicitly say 'what about North Bangalore').
    7. Return ONLY the updated JSON string. No markdown, no explanation.
    """
    try:
        response = model.generate_content(prompt)
        # Clean response to get pure JSON
        cleaned_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"Error extraction: {e}")
        return current_prefs

def generate_sales_response(user_input, matches, preferences):
    """
    Generates a conversational response and sales pitch.
    """
    match_count = len(matches)
    matches_str = matches.to_string() if not matches.empty else "No direct matches found."
    
    prompt = f"""
    You are an expert Real Estate Agent interacting with a customer on a call.
    
    User Input: "{user_input}"
    Current Preferences: {json.dumps(preferences)}
    
    Found {match_count} Properties matching the criteria.
    Available Matches (Sample):
    {matches_str}
    
    Task:
    1. Acknowledge the user's request enthusiastically.
    2. analyze the 'Found {match_count} Properties':
       - If {match_count} > 5 OR if the user request is very broad:
         * Mention you have found {match_count} great options (which are displayed).
         * Ask CLARIFYING QUESTIONS to help narrow down the selection from this list. (e.g., "I've pulled up {match_count} properties for you. To help us zero in on the best one, what is your budget range?").
       - If {match_count} <= 5:
         * Pitch the specific options. Highlight why they fit.
         * Treat them as a "shortlist" for the user to consider.
         * Ask which one they would like to explore further.
         * Do NOT immediately assume one is the "perfect" choice unless it's the only one.
         
    3. Keep the tone professional, persuasive, and conversational.
    4. Do NOT output JSON. Output natural language text.
    """
    response = model.generate_content(prompt)
    return response.text

# --- UI Layout ---

st.title("📞 AI Real Estate Agent")
st.markdown("*Conversational Property Matcher & Pitch Generator*")

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input
if prompt := st.chat_input("Describe what you are looking for..."):
    # 1. User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Extract Intent
    with st.spinner("Analyzing request..."):
        new_prefs = extract_intent(prompt, st.session_state.user_preferences)
        st.session_state.user_preferences = new_prefs
        
        # Debug: Show internal state in sidebar
        st.sidebar.json(st.session_state.user_preferences)

    # 3. Search Data
    matches = search_properties(new_prefs, df)
    
    # 4. Generate Response
    with st.spinner("Finding matches & preparing pitch..."):
        ai_response = generate_sales_response(prompt, matches, new_prefs)
    
    # 5. Assistant Message
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    with st.chat_message("assistant"):
        st.markdown(ai_response)
        
        # 6. Display Properties as Cards
        if not matches.empty:
            st.markdown("### 🏘️ Recommended Properties")
            
            # Create a grid 
            # We iterate through matches and place them in columns
            cols = st.columns(4)
            for idx, (_, row) in enumerate(matches.iterrows()):
                col = cols[idx % 4]
                with col:
                    with st.container(border=True):
                        st.subheader(f"{row.get('Project Name', 'N/A')}")
                        st.caption(f"by {row.get('Developer', 'Unknown')}")
                        st.markdown(f"📍 **{row.get('Location', 'N/A')}**")
                        st.markdown(f"💰 **{row.get('Price per sqft (Enriched)', 'Ask')}**")
                        st.markdown(f"🏗️ {row.get('Project Status', 'N/A')}")
                        with st.expander("Details"):
                            st.markdown(f"**Type:** {row.get('Project Type', 'N/A')}")
                            st.markdown(f"**RERA:** {row.get('RERA Status (Enriched)', 'Pending')}")
                            st.markdown(f"**Amenities:** {row.get('Key Amenities', 'Not listed')}")
