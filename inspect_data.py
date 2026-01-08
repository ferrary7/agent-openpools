
import pandas as pd

try:
    df = pd.read_excel('banglore_pools.xlsx')
    print("Columns:")
    print(df.columns.tolist())
    print("\nFirst 3 rows:")
    print(df.head(3).to_string())
    print("\nData Types:")
    print(df.dtypes)
except Exception as e:
    print(f"Error reading excel: {e}")
