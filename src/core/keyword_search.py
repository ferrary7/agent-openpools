import pandas as pd
from typing import Dict, List, Any

class KeywordSearchEngine:
    """Simple, accurate keyword-based search engine"""
    
    def __init__(self):
        # Load property data
        self.df = pd.read_excel('banglore_pools.xlsx')
        print(f"✅ Keyword Search Engine initialized with {len(self.df)} properties")
    
    def search(self, criteria: Dict[str, Any], limit: int = 20) -> pd.DataFrame:
        """
        Search properties using Weighted Keyword Matching (TF-IDF style)
        
        Logic:
        1. Calculate rarity of each user keyword in the dataset (Inverse Document Frequency)
        2. Score each property: Sum of weights of matched keywords
        3. Return top scoring properties
        
        Why this works better:
        - "KIADB" (Rare, specific) -> Matching this gives high score
        - "North Bangalore" (Common, generic) -> Matching this gives low score
        - Property matching "KIADB" but missing "Airport" will still rank HIGH because KIADB is specific.
        """
        
        filtered = self.df.copy()
        print(f"\n🔍 Starting search with {len(filtered)} properties")
        
        keywords = criteria.get('keywords', [])
        
        # 1. PRICE FILTERING (Hard filter - budget is usually strict)
        if criteria.get('max_price') and criteria['max_price'] > 0:
            def parse_price(price_str):
                try:
                    price_str = str(price_str).replace('₹', '').replace(',', '').replace('~', '').strip()
                    if '-' in price_str:
                        price_str = price_str.split('-')[0].strip()
                    return float(price_str) if price_str and price_str != 'nan' else 0
                except:
                    return 0
            
            filtered['parsed_price'] = filtered['Price per sqft (Enriched)'].apply(parse_price)
            # Allow 10% buffer
            filtered = filtered[filtered['parsed_price'] <= (criteria['max_price'] * 1.1)]
            print(f"💰 Price Filter: {len(filtered)} properties remain")

        # 2. WEIGHTED KEYWORD SEARCH
        if keywords and len(keywords) > 0:
            print(f"📍 Keywords: {', '.join(keywords)}")
            
            # A. Calculate Keyword Weights (IDF - Inverse Document Frequency)
            keyword_weights = {}
            total_docs = len(self.df)
            
            for kw in keywords:
                # Count how many properties have this keyword
                matches = self.df.apply(lambda row: self._matches_keyword(row, kw), axis=1).sum()
                
                # Weight = Log(Total / (Matches + 1)) 
                # Simpler approximation: Higher rarity = Higher weight
                if matches > 0:
                    weight = 100 / matches  # Rare = High Score
                else:
                    weight = 0
                    
                keyword_weights[kw] = weight
                print(f"   ⚖️  Weight for '{kw}': {weight:.2f} (Found in {matches} props)")

            # B. Score Properties
            def calculate_score(row):
                score = 0
                matched_terms = []
                
                # Check each keyword
                for kw, weight in keyword_weights.items():
                    keyword_parts = kw.split()
                    
                    # 1. Check Project Name (Critical - 10x Bonus - "I want specific project")
                    proj_name = str(row.get('Project Name', '')).lower()
                    if all(part.lower() in proj_name for part in keyword_parts):
                        score += (weight * 10)
                        matched_terms.append(kw)
                        continue

                    # 2. Check Developer (High - 5x Bonus - "I want Sobha/Prestige")
                    dev_name = str(row.get('Developer', '')).lower()
                    if all(part.lower() in dev_name for part in keyword_parts):
                        score += (weight * 5)
                        matched_terms.append(kw)
                        continue

                    # 3. Check Location Column (Primary - 3x Bonus)
                    loc_text = str(row.get('Location', '')).lower()
                    if all(part.lower() in loc_text for part in keyword_parts):
                        score += (weight * 3)  
                        matched_terms.append(kw)
                        continue
                        
                    # 4. Check Region/Nearby (Secondary - Normal Weight)
                    other_text = ' '.join([
                        str(row.get('Region', '')),
                        str(row.get('Nearby Developments', '')),
                        str(row.get('Key Amenities', ''))
                    ]).lower()
                    
                    if all(part.lower() in other_text for part in keyword_parts):
                        score += weight
                        matched_terms.append(kw)
                        
                return score, matched_terms

            # Apply scoring
            results = filtered.apply(calculate_score, axis=1)
            filtered['search_score'] = results.apply(lambda x: x[0])
            filtered['matched_terms'] = results.apply(lambda x: x[1])
            
            # C. Filter & Sort
            # Keep properties with score > 0 (matched at least something)
            filtered = filtered[filtered['search_score'] > 0]
            
            # Sort by score descending
            filtered = filtered.sort_values('search_score', ascending=False)
            
            print(f"✅ Found {len(filtered)} matches after scoring")
            if not filtered.empty:
                top = filtered.iloc[0]
                print(f"🎯 Top Match: {top['Project Name']} (Score: {top['search_score']:.2f})")
                print(f"   Matched: {top['matched_terms']}")

        return filtered.head(limit)

    def _matches_keyword(self, row, keyword):
        """Helper: Does flexible match of keyword parts against row"""
        keyword_parts = keyword.split()
        search_text = ' '.join([
            str(row.get('Project Name', '')),
            str(row.get('Developer', '')),
            str(row.get('Location', '')),
            str(row.get('Region', '')),
            str(row.get('Nearby Developments', ''))
        ]).lower()
        return all(part.lower() in search_text for part in keyword_parts)

    def _rank_results(self, df: pd.DataFrame, keywords: List[str]) -> pd.DataFrame:
        """Deprecated - logic moved to search"""
        return df
    
    def _rank_results(self, df: pd.DataFrame, keywords: List[str]) -> pd.DataFrame:
        """Rank properties by keyword match count"""
        
        if len(keywords) == 0:
            return df
        
        ranked = df.copy()
        
        # Count keyword occurrences in Location (primary)
        def count_keyword_matches(location_str):
            location_str = str(location_str).lower()
            return sum(location_str.count(kw.lower()) for kw in keywords)
        
        ranked['keyword_score'] = ranked['Location'].apply(count_keyword_matches)
        
        # Sort by keyword score (descending)
        ranked = ranked.sort_values('keyword_score', ascending=False)
        
        print(f"🎯 Top property has {ranked['keyword_score'].max()} keyword matches")
        
        return ranked
    
    def get_property_context(self, property_row: pd.Series) -> str:
        """Get property context for LLM"""
        parts = []
        
        parts.append(f"**{property_row.get('Project Name', 'Unknown')}** by {property_row.get('Developer', 'Unknown')}")
        parts.append(f"Location: {property_row.get('Location', 'Unknown')}")
        parts.append(f"Type: {property_row.get('Project Type', 'Unknown')}")
        parts.append(f"Price: ₹{property_row.get('Price per sqft (Enriched)', 'N/A')} per sq ft")
        
        if pd.notna(property_row.get('Project Status')):
            parts.append(f"Status: {property_row['Project Status']}")
        
        return " | ".join(parts)
