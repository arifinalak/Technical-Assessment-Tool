import sqlite3
import pandas as pd
from datetime import timedelta

con = sqlite3.connect('sales.db')
df = pd.read_sql('SELECT * FROM sales', con)

# Base it on 2023 data for forecasting
df_2023 = df[df['year'] == 2023].copy()

# Forecast 2025 (+15% growth from 2023)
df_2025 = df_2023.copy()
df_2025['year'] = 2025
df_2025['order_date'] = pd.to_datetime(df_2025['order_date']) + pd.DateOffset(years=2)
df_2025['order_date'] = df_2025['order_date'].dt.strftime('%Y-%m-%d')
df_2025['year_month'] = df_2025['order_date'].str[:7]
df_2025['order_id'] = ['FCST-25-' + str(i).zfill(5) for i in range(len(df_2025))]
df_2025['order_status'] = 'Forecasted'
df_2025['revenue'] = df_2025['revenue'] * 1.15
df_2025['cost'] = df_2025['cost'] * 1.15
df_2025['profit'] = df_2025['profit'] * 1.15
df_2025['gross_sales'] = df_2025['gross_sales'] * 1.15
df_2025['profit_after_shipping'] = df_2025['profit_after_shipping'] * 1.15

# Forecast 2026 (+32% growth from 2023)
df_2026 = df_2023.copy()
df_2026['year'] = 2026
df_2026['order_date'] = pd.to_datetime(df_2026['order_date']) + pd.DateOffset(years=3)
df_2026['order_date'] = df_2026['order_date'].dt.strftime('%Y-%m-%d')
df_2026['year_month'] = df_2026['order_date'].str[:7]
df_2026['order_id'] = ['FCST-26-' + str(i).zfill(5) for i in range(len(df_2026))]
df_2026['order_status'] = 'Forecasted'
df_2026['revenue'] = df_2026['revenue'] * 1.32
df_2026['cost'] = df_2026['cost'] * 1.32
df_2026['profit'] = df_2026['profit'] * 1.32
df_2026['gross_sales'] = df_2026['gross_sales'] * 1.32
df_2026['profit_after_shipping'] = df_2026['profit_after_shipping'] * 1.32

# Combine and save
forecast_df = pd.concat([df_2025, df_2026])
forecast_df.to_sql('sales', con, if_exists='append', index=False)

print(f"Added {len(df_2025)} rows for 2025 and {len(df_2026)} rows for 2026.")
con.close()
