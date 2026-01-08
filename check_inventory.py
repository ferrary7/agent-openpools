
import pandas as pd

try:
    df = pd.read_excel('banglore_pools.xlsx')
    # Normalize
    df.columns = [c.strip() for c in df.columns]
    
    # Check Location counts
    if 'Location' in df.columns:
        print("Top Locations by count:")
        print(df['Location'].value_counts().head(10))
    
    # Check Price distribution if possible (optional, just location is usually enough for a broad match)
    
except Exception as e:
    print(f"Error: {e}")
