import pandas as pd

df = pd.read_parquet('logos.snappy.parquet')
domains = df['domain'].tolist()

print(f"Processing {len(domains)} domains")