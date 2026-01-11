import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

class SimpleExtractor:
    """Simple extraction - ONLY extract what user explicitly mentions"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        print("✅ Simple Extractor initialized")
    
    def extract(self, user_message: str) -> dict:
        """Extract search criteria - NO expansion, ONLY user-mentioned keywords"""
        
        prompt = f"""You are a property search criteria extractor.

EXTRACTION RULES:
1. Extract ONLY what the user explicitly mentions
2. DO NOT expand or infer additional keywords
3. If user says "KIADB", extract ["KIADB"] - nothing more
4. If user says "North Bangalore near Airport", extract ["North Bangalore", "Airport"]

USER MESSAGE:
"{user_message}"

EXTRACT as JSON:
{{
    "keywords": [<ONLY keywords user explicitly said, e.g., ["KIADB", "Airport"]>],
    "bedrooms": <number or null>,
    "max_price": <number in rupees or null>,
    "min_price": <number in rupees or null>,
    "developers": [<ONLY explicitly mentioned developer names>],
    "project_type": "<type or null>",
    "possession": "<possession status or null>",
    "investment_goal": <true if investment/ROI mentioned, else false>,
    "amenities": [<list of amenities if mentioned>]
}}

CRITICAL:
- keywords: ONLY what user said (e.g., ["North Bangalore", "Airport", "KIADB"])
- NO expansion (don't add Devanahalli, Thanisandra, etc.)
- NO inference (don't assume anything)
- Return ONLY valid JSON, no explanation
"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Remove markdown code blocks
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            
            criteria = json.loads(response_text)
            
            print(f"📋 Extracted Criteria: {json.dumps(criteria, indent=2)}")
            return criteria
            
        except Exception as e:
            print(f"❌ Extraction error: {e}")
            return {}
