import sqlite3
import pandas as pd
from werkzeug.security import generate_password_hash as h

CSV = "Test_sales_dataset_ecommerce_sales_dataset_.csv"   # use pd.read_excel for the .xlsx
df = pd.read_csv(CSV)
df = df.rename(columns={"Profit_Margin_%": "profit_margin_pct"})
df.columns = [c.lower() for c in df.columns]

# dates are M/D/YYYY -> store ISO so text sorting and SQL date logic work
d = pd.to_datetime(df["order_date"], format="%m/%d/%Y")
df["order_date"] = d.dt.strftime("%Y-%m-%d")
df["year_month"] = d.dt.strftime("%Y-%m")

# derived columns (profit = revenue - cost; shipping is NOT deducted in the source)
df["gross_sales"] = (df["unit_price"] * df["quantity"]).round(2)
df["discount_amount"] = (df["gross_sales"] - df["revenue"]).round(2)
df["profit_after_shipping"] = (df["profit"] - df["shipping_cost"]).round(2)
df["is_loss"] = (df["profit"] < 0).astype(int)

con = sqlite3.connect("sales.db")
df.to_sql("sales", con, if_exists="replace", index=False)
con.close()

users = [  # username, password, role, scope (NULL = no row restriction)
    ("admin",      "admin123",   "admin",            None),
    ("asia_mgr",   "asia123",    "regional_manager", "Asia"),
    ("europe_mgr", "europe123",  "regional_manager", "Europe"),
    ("analyst",    "analyst123", "sales_analyst",    None),
    ("logistics",  "logi123",    "logistics",        None),
]
a = sqlite3.connect("auth.db")
a.execute("DROP TABLE IF EXISTS users")
a.execute("CREATE TABLE users(username TEXT PRIMARY KEY, pw TEXT, role TEXT, scope TEXT)")
a.execute("DROP TABLE IF EXISTS audit")
a.execute("CREATE TABLE audit(ts TEXT, username TEXT, role TEXT, action TEXT, detail TEXT)")
a.executemany("INSERT INTO users VALUES(?,?,?,?)", [(u, h(p), r, s) for u, p, r, s in users])
a.commit()
print("rows:", len(df), "| columns:", len(df.columns), "| users:", len(users))
