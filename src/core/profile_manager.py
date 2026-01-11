
import json
import os
import uuid
from datetime import datetime

class ProfileManager:
    def __init__(self, data_path='data/profiles.json'):
        self.data_path = data_path
        self.data = self._load_data()

    def _load_data(self):
        if not os.path.exists(self.data_path):
            return {"users": {}}
        try:
            with open(self.data_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"users": {}}

    def _save_data(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get_or_create_user(self, user_id, name="Guest"):
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {
                "profile": {"name": name, "joined_at": str(datetime.now())},
                "funnels": [],
                "active_funnel_id": None
            }
            self._save_data()
        return self.data["users"][user_id]

    def create_funnel(self, user_id, funnel_name="New Search"):
        user = self.get_or_create_user(user_id)
        funnel_id = str(uuid.uuid4())
        
        new_funnel = {
            "id": funnel_id,
            "name": funnel_name,
            "created_at": str(datetime.now()),
            "criteria": {},  # Stores filters: location, price, etc.
            "status": "active"
        }
        
        user["funnels"].append(new_funnel)
        user["active_funnel_id"] = funnel_id
        self._save_data()
        return new_funnel

    def get_active_funnel(self, user_id):
        user = self.get_or_create_user(user_id)
        if not user["active_funnel_id"]:
            return self.create_funnel(user_id)
            
        # Find the funnel object
        for f in user["funnels"]:
            if f["id"] == user["active_funnel_id"]:
                return f
        
        # Fallback if ID mismatch
        return self.create_funnel(user_id)

    def update_funnel_criteria(self, user_id, funnel_id, new_criteria):
        user = self.data["users"].get(user_id)
        if not user: return None
        
        for f in user["funnels"]:
            if f["id"] == funnel_id:
                # Merge logic
                current = f.get("criteria", {})
                
                # Update keys. If value is None, remove the key.
                for k, v in new_criteria.items():
                    if v is None:
                        if k in current:
                            del current[k]
                    else:
                        current[k] = v
                
                f["criteria"] = current
                f["updated_at"] = str(datetime.now())
                self._save_data()
                return f
        return None

    def switch_funnel(self, user_id, funnel_id):
        user = self.data["users"].get(user_id)
        if user:
            user["active_funnel_id"] = funnel_id
            self._save_data()
