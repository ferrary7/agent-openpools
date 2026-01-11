import google.generativeai as genai
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

class ContextAwareSalesAgent:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        print("✅ Context-Aware Sales Agent initialized")
    
    def generate_response(self, criteria: dict, properties: pd.DataFrame, user_message: str) -> str:
        """Generate intelligent, data-driven sales response"""
        
        if properties.empty:
            return self._no_results_response(criteria)
        
        # Build property context
        property_contexts = []
        for idx, row in properties.head(5).iterrows():  # Top 5 properties
            context = f"""
**{row.get('Project Name', 'Unknown')}** by {row.get('Developer', 'Unknown')}
- Location: {row.get('Location', 'Unknown')}
- Type: {row.get('Project Type', 'Unknown')}
- Price: ₹{row.get('Price per sqft (Enriched)', 'N/A')} per sq ft
- Status: {row.get('Project Status', 'N/A')}
- Match Score: {row.get('search_score', 0):.1f} (Matches: {row.get('matched_terms', [])})
"""
            property_contexts.append(context)
        
        properties_text = "\n".join(property_contexts)
        
        # Build prompt
        prompt = f"""You are an expert real estate sales agent with deep market knowledge.

USER CRITERIA:
{criteria}

USER MESSAGE:
"{user_message}"

TOP MATCHING PROPERTIES:
{properties_text}

TOTAL MATCHES: {len(properties)}

GENERATE A RESPONSE THAT:
1. **Acknowledges ALL requirements** (explicit + implicit, including investment goals if mentioned)
2. **Highlights top 3-5 properties** with specific reasons why they match
3. **Provides data-driven insights**:
   - Why these locations are good for investment (if investment goal mentioned)
   - Developer track record and tier
   - Appreciation potential
4. **Asks ONE intelligent follow-up question** to narrow down further

TONE: Professional, consultative, data-driven
LENGTH: 3-4 paragraphs maximum

CRITICAL:
- If user mentioned "3x returns" or investment goals, ADDRESS THIS DIRECTLY
- If user mentioned "category builders", explain which Tier 1 developers are included
- Provide specific numbers and facts, not generic statements
- Focus on the TOP 3 properties, not all {len(properties)}
"""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"❌ Sales agent error: {e}")
            return f"I found {len(properties)} properties matching your criteria. Let me show you the top options."
    
    def _no_results_response(self, criteria: dict) -> str:
        """Generate helpful response when no properties match"""
        return f"""I understand you're looking for properties matching your criteria, but I couldn't find exact matches in our current inventory. 

Let me suggest some alternatives:
1. **Expand the location** - Would you consider nearby areas?
2. **Adjust the budget** - I can show you options slightly above or below your range
3. **Different developers** - I can recommend other reputable builders

What would you prefer?"""
