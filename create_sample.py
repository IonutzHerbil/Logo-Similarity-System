import pandas as pd
df = pd.read_parquet('logos.snappy.parquet')
sample = df.head(50)
sample.to_parquet('logos_sample_50.parquet', compression='snappy')

print(f'Created sample with {len(sample)} websites')
print('Sample websites:')
for i, domain in enumerate(sample['domain'].head(10), 1):
    print(f'  {i}. {domain}')
print('  ...')
