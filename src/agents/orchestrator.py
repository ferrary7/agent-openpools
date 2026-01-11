
import google.generativeai as genai
import json

class OrchestratorAgent:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def decide_action(self, user_input, active_funnel):
        """
        Decides if we should STAY in current funnel or CREATE new one.
        Returns: {'action': 'UPDATE' | 'NEW', 'reason': '...'}
        """
        prompt = f"""
        You are the Orchestrator. Manage User Search Intent.
        
        Active Funnel: "{active_funnel.get('name', 'General')}"
        Active Criteria: {json.dumps(active_funnel.get('criteria', {}))}
        
        User Input: "{user_input}"
        
        Task:
        - Detect if the user is continuing the current search OR starting a completely new topic.
        - Example Continue: "What is the price?", "Show me 3BHKs there".
        - Example New: "Actually, look at North Bangalore", "Start over", "Search for Brigade properties instead".
        
        Output JSON:
        {{
            "action": "UPDATE" or "NEW",
            "suggested_funnel_name": "Name of new funnel if NEW"
        }}
        """
        try:
            res = self.model.generate_content(prompt)
            clean = res.text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean)
        except:
            return {"action": "UPDATE"}
