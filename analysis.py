"""Generates DATA_ANALYSIS.md: the written data analysis behind the dashboard. Run: python analysis.py"""
import pandas as pd

df = pd.read_csv("Test_sales_dataset_ecommerce_sales_dataset_.csv")
NCOLS = df.shape[1]
df["d"] = pd.to_datetime(df["Order_Date"], format="%m/%d/%Y")
NETS = ["Delivered", "Processing"]
net = df[df.Order_Status.isin(NETS)]
out = []
def h(t): out.append("\n## " + t + "\n")
def p(t): out.append(t + "\n")
def table(frame, floatfmt="{:,.1f}"):
    cols = [frame.index.name or ""] + [str(c) for c in frame.columns]
    out.append("| " + " | ".join(cols) + " |"); out.append("|" + "---|" * len(cols))
    for idx, r in frame.iterrows():
        out.append("| " + " | ".join([str(idx)] + [floatfmt.format(v) if isinstance(v, float) else f"{v:,}" if isinstance(v, int) else str(v) for v in r]) + " |")
    out.append("")

out.append("# Data analysis: Test sales dataset\n")
p(f"Source: `Test_sales_dataset_ecommerce_sales_dataset_.csv`. {len(df):,} orders, {NCOLS} columns, "
  f"{df.d.min():%Y-%m-%d} to {df.d.max():%Y-%m-%d}.")
h("1. Data quality")
p(f"- Missing values: {int(df.isna().sum().sum())}. Duplicate rows: {int(df.duplicated().sum())}. Order IDs unique: {df.Order_ID.is_unique}.")
rev_ok = ((df.Unit_Price * df.Quantity * (1 - df.Discount)).round(2) - df.Revenue).abs().le(0.05).all()
prof_ok = (df.Revenue - df.Cost - df.Profit).abs().le(0.05).all()
p(f"- Revenue = Unit_Price x Quantity x (1 - Discount) holds in every row: {rev_ok}.")
p(f"- Profit = Revenue - Cost holds in every row: {prof_ok}. Shipping cost is therefore not deducted from profit.")
p(f"- Customer_ID: {df.Customer_ID.nunique():,} unique IDs, but one ID can appear with several segments, genders and regions "
  f"(max {df.groupby('Customer_ID').Region.nunique().max()} regions), so customer-level conclusions are unreliable.")
h("2. Headline numbers")
p(f"- Gross revenue (all orders): {df.Revenue.sum():,.2f}. Net revenue (Delivered + Processing): {net.Revenue.sum():,.2f}.")
p(f"- Net profit: {net.Profit.sum():,.2f}. Net weighted margin (profit / revenue): {net.Profit.sum() / net.Revenue.sum() * 100:.1f}%. "
  f"Across all orders the weighted margin is {df.Profit.sum() / df.Revenue.sum() * 100:.1f}%, while the simple average of row margins is "
  f"{df['Profit_Margin_%'].mean():.1f}%, which understates it, so dashboards use the weighted figure.")
p(f"- Order status: " + ", ".join(f"{k} {v:,} ({v / len(df) * 100:.1f}%)" for k, v in df.Order_Status.value_counts().items()) + ".")
p(f"- Cancelled + Returned orders carry {df[~df.Order_Status.isin(NETS)].Revenue.sum():,.0f} of revenue "
  f"({df[~df.Order_Status.isin(NETS)].Revenue.sum() / df.Revenue.sum() * 100:.0f}% of gross), so net revenue is the right default KPI.")
h("3. Discounts destroy margin")
t = df.groupby("Discount").agg(orders=("Order_ID", "count"), avg_margin_pct=("Profit_Margin_%", "mean"), loss_share_pct=("Profit", lambda s: (s < 0).mean() * 100))
t.index = [f"{x:.0%}" for x in t.index]; t.index.name = "Discount"; table(t)
p(f"{(df.Profit < 0).sum():,} orders ({(df.Profit < 0).mean() * 100:.1f}%) lose money. Losses begin at discounts of 30% and above.")
h("4. Category and region (net)")
c = net.groupby("Category").agg(revenue=("Revenue", "sum"), profit=("Profit", "sum")).sort_values("revenue", ascending=False)
c["profit_share_pct"] = c.profit / c.profit.sum() * 100; c = c.round(1); table(c)
r = net.groupby("Region").agg(revenue=("Revenue", "sum"), profit=("Profit", "sum"), orders=("Order_ID", "count")).sort_values("revenue", ascending=False).round(0); table(r, "{:,.0f}")
p("Electronics generates roughly two thirds of net profit. Regions are evenly balanced.")
h("5. Returns and cancellations by category")
rc = df.groupby("Category").Order_Status.apply(lambda s: pd.Series({"returned_pct": (s == "Returned").mean() * 100, "cancelled_pct": (s == "Cancelled").mean() * 100})).unstack().round(1)
table(rc)
h("6. Shipping")
s = df.groupby("Shipping_Method").agg(avg_cost=("Shipping_Cost", "mean"), avg_days=("Shipping_Days", "mean")).round(1); table(s)
p("Cost differs strongly by method, but delivery time is almost identical. Faster methods are not faster in this data.")
h("7. Time pattern (caution)")
y = df.groupby(df.d.dt.year).size().rename("orders").to_frame(); y.index.name = "Year"; table(y)
m = df.groupby(df.d.dt.to_period("M")).size()
p(f"Orders peak in {m.idxmax()} ({m.max()}) and fall to {m.iloc[-1]} in {m.index[-1]}. This looks like an artefact of how the "
  f"sample was generated and should not be presented as a real business decline.")
open("DATA_ANALYSIS.md", "w", encoding="utf-8").write("\n".join(out))
print("wrote DATA_ANALYSIS.md")
