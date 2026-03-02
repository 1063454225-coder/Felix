import pandas as pd

df = pd.read_excel('SH603893_20260218_011552.xlsx', sheet_name=None)
print('Sheet names:', list(df.keys()))
print('\nSheet content:')
for sheet_name, sheet_df in df.items():
    print(f'\n{sheet_name}:')
    print(f'  Shape: {sheet_df.shape}')
    print(f'  Columns: {sheet_df.columns.tolist()[:10]}')
    print(f'  Last few rows:')
    print(sheet_df.tail(10))