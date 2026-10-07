"""Data access, role-based scoping and all analytics. Every number shown in the app comes from here."""
import sqlite3
import numpy as np
import pandas as pd

DF = pd.read_sql("SELECT * FROM sales", sqlite3.connect("sales.db"))
NET = ["Delivered", "Processing"]          # statuses that count as "net" sales

FINANCE = {"cost", "profit", "profit_margin_pct", "profit_after_shipping", "is_loss"}
CUSTOMER = {"customer_id", "customer_gender"}
PRICING = {"unit_price", "discount", "revenue", "gross_sales", "discount_amount"}
ALL_TIERS = ["ops", "sales", "finance"]

ROLES = {   # row_scope = column the user is locked to; hide = columns they never see
    "admin": {"label": "Administrator", "row_scope": None, "hide": set(), "tiers": ALL_TIERS,
              "desc": "Every row and every column, plus the user list and audit log."},
    "regional_manager": {"label": "Regional manager", "row_scope": "region", "hide": set(),
                         "tiers": ALL_TIERS,
                         "desc": "All columns, but only the rows of their own region."},
    "sales_analyst": {"label": "Sales analyst", "row_scope": None, "hide": FINANCE | CUSTOMER,
                      "tiers": ["ops", "sales"],
                      "desc": "All regions, but no cost, profit, margin or customer-level columns."},
    "logistics": {"label": "Logistics", "row_scope": None, "hide": FINANCE | CUSTOMER | PRICING,
                  "tiers": ["ops"],
                  "desc": "Orders, status, shipping and payment only. No prices, revenue or profit."},
}

def scoped(user):
    """The ONLY way data leaves this module: row filter + column projection."""
    cfg = ROLES[user["role"]]
    d = DF
    if cfg["row_scope"]:
        d = d[d[cfg["row_scope"]] == user["scope"]]
    return d[[c for c in d.columns if c not in cfg["hide"]]].copy()

def apply_filters(d, year="", category="", region="", segment="", status=""):
    if year:
        d = d[d["year"] == int(year)]
    if category:
        d = d[d["category"] == category]
    if region and "region" in d:
        d = d[d["region"] == region]
    if segment:
        d = d[d["customer_segment"] == segment]
    if status:
        d = d[d["order_status"].isin(status.split(","))]
    return d

def fmt(x):
    x = float(x)
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(x) >= div:
            return f"{x / div:.2f}{unit}"
    return f"{x:,.0f}"

def _clean(s):
    return s.replace([np.inf, -np.inf], 0).fillna(0)

# ------------------------------------------------------------------ KPIs
def build_kpis(d, d_all):
    k = {"orders": int(len(d))}
    if "revenue" in d:
        k["revenue"] = round(float(d["revenue"].sum()), 2)
        k["avg_order_value"] = round(float(d["revenue"].mean()), 2) if len(d) else 0.0
    if "profit" in d:
        k["profit"] = round(float(d["profit"].sum()), 2)
    if {"profit", "revenue"} <= set(d.columns) and d["revenue"].sum() > 0:
        k["margin_pct"] = round(100 * float(d["profit"].sum() / d["revenue"].sum()), 1)
    if len(d_all):
        k["return_rate_pct"] = round(100 * float((d_all["order_status"] == "Returned").mean()), 1)
        k["cancel_rate_pct"] = round(100 * float((d_all["order_status"] == "Cancelled").mean()), 1)
    return k

def build_spark(d):
    g = d.groupby("year_month")
    out = {"labels": g.size().index.tolist(), "orders": g.size().tolist()}
    if "revenue" in d:
        out["revenue"] = g["revenue"].sum().round(2).tolist()
        out["avg_order_value"] = g["revenue"].mean().round(2).tolist()
    if "profit" in d:
        out["profit"] = g["profit"].sum().round(2).tolist()
    if {"profit", "revenue"} <= set(d.columns):
        out["margin_pct"] = _clean(g["profit"].sum() / g["revenue"].sum() * 100).round(1).tolist()
    return out

# ------------------------------------------------------------------ charts
# series = (column, aggregation, legend name). Charts adapt to the columns a role may see.
CHARTS = [
 dict(id="trend", title="Revenue and profit over time", title1="Revenue over time", alt="Orders over time",
      type="line", by="year_month", span=8, fmt="money",
      series=[("revenue", "sum", "Revenue"), ("profit", "sum", "Profit")],
      note="Volume peaks in 2023 and tails off in 2024: a property of this sample, not a trend to over-read."),
 dict(id="status", title="Order status mix", type="doughnut", by="order_status", span=4, fmt="count",
      series=[("order_id", "count", "Orders")], all_status=True),
 dict(id="category", title="Revenue and profit by category", title1="Revenue by category",
      alt="Orders by category", type="bar", by="category", span=6, fmt="money", sort=True,
      series=[("revenue", "sum", "Revenue"), ("profit", "sum", "Profit")]),
 dict(id="country", title="Top countries", alt="Orders by country", type="hbar", by="country", span=6,
      fmt="money", sort=True, top=8, series=[("revenue", "sum", "Revenue")]),
 dict(id="discount", title="Discount depth vs margin", type="bar", by="discount", span=6, fmt="pct",
      series=[("profit_margin_pct", "mean", "Average margin %"), ("is_loss", "pct", "Loss-making orders %")],
      note="Margins collapse from 30% discounts upward."),
 dict(id="products", title="Top 10 products", alt="Most ordered products", type="hbar", by="product_name",
      span=6, fmt="money", sort=True, top=10, series=[("revenue", "sum", "Revenue")]),
 dict(id="region", title="Revenue by region", alt="Orders by region", type="bar", by="region", span=4,
      fmt="money", multi=True, series=[("revenue", "sum", "Revenue")]),
 dict(id="segment", title="Customer segments", alt="Orders by segment", type="doughnut",
      by="customer_segment", span=4, fmt="money", series=[("revenue", "sum", "Revenue")]),
 dict(id="ship", title="Average shipping cost by method", type="bar", by="shipping_method", span=4,
      fmt="money", sort=True, series=[("shipping_cost", "mean", "Avg shipping cost")]),
 dict(id="payment", title="Orders by payment method", type="hbar", by="payment_method", span=6,
      fmt="count", sort=True, series=[("order_id", "count", "Orders")]),
]

def _agg(g, metric, agg):
    if agg == "count":
        return g[metric].count()
    if agg == "pct":
        return g[metric].mean() * 100
    return g[metric].agg(agg)

def build_charts(d, d_all):
    out = []
    for c in CHARTS:
        src = d_all if c.get("all_status") else d
        if c["by"] not in src.columns:
            continue
        if c.get("multi") and src[c["by"]].nunique() < 2:
            continue
        series = [s for s in c["series"] if s[0] in src.columns]
        title, fm = c["title"], c["fmt"]
        if not series:
            if "alt" not in c:
                continue
            series, title, fm = [("order_id", "count", "Orders")], c["alt"], "count"
        elif len(series) < len(c["series"]):
            title = c.get("title1", title)
        g = src.groupby(c["by"])
        frame = pd.DataFrame({n: _clean(_agg(g, m, a)) for m, a, n in series})
        if c.get("sort"):
            frame = frame.sort_values(frame.columns[0], ascending=False)
        if c.get("top"):
            frame = frame.head(c["top"])
        labels = [f"{round(x * 100)}%" for x in frame.index] if c["by"] == "discount" \
            else frame.index.astype(str).tolist()
        out.append(dict(id=c["id"], title=title, type=c["type"], span=c["span"], fmt=fm, note=c.get("note", ""),
                        labels=labels,
                        series=[{"name": n, "values": frame[n].round(2).tolist()} for n in frame.columns]))
    return out

def build_heatmap(d):
    metric = "revenue" if "revenue" in d else "order_id"
    p = d.pivot_table(index="year", columns="month", values=metric,
                      aggfunc="sum" if metric == "revenue" else "count", fill_value=0)
    p = p.reindex(columns=range(1, 13), fill_value=0)
    return {"title": "Seasonality heatmap: " + ("revenue" if metric == "revenue" else "orders") + " by month",
            "rows": [int(i) for i in p.index], "cols": list(range(1, 13)),
            "values": p.round(0).values.tolist(), "fmt": "money" if metric == "revenue" else "count"}

# ------------------------------------------------------------------ explorer
DIMS = {"year": "Year", "quarter": "Quarter", "season": "Season", "year_month": "Month", "region": "Region",
        "country": "Country", "category": "Category", "sub_category": "Sub-category",
        "product_name": "Product", "customer_segment": "Customer segment",
        "customer_gender": "Customer gender", "shipping_method": "Shipping method",
        "payment_method": "Payment method", "order_status": "Order status", "discount": "Discount level"}
NATURAL = {"year", "quarter", "year_month", "discount", "season"}
METRICS = {"orders": ("Orders", set(), "count"), "revenue": ("Revenue", {"revenue"}, "money"),
           "profit": ("Profit", {"profit"}, "money"), "margin": ("Margin %", {"profit", "revenue"}, "pct"),
           "aov": ("Average order value", {"revenue"}, "money"), "units": ("Units sold", {"quantity"}, "count"),
           "shipping": ("Average shipping cost", {"shipping_cost"}, "money"),
           "avg_discount": ("Average discount %", {"discount"}, "pct"),
           "loss_rate": ("Loss-making orders %", {"is_loss"}, "pct")}

def available_dims(cols):
    return [{"key": k, "label": v} for k, v in DIMS.items() if k in cols]

def available_metrics(cols):
    return [{"key": k, "label": v[0], "fmt": v[2]} for k, v in METRICS.items() if v[1] <= set(cols)]

def explore(d, dim, metric, top=0, sort="desc"):
    g = d.groupby(dim)
    if metric == "orders":
        s = g.size()
    elif metric == "revenue":
        s = g["revenue"].sum()
    elif metric == "profit":
        s = g["profit"].sum()
    elif metric == "margin":
        s = g["profit"].sum() / g["revenue"].sum() * 100
    elif metric == "aov":
        s = g["revenue"].mean()
    elif metric == "units":
        s = g["quantity"].sum()
    elif metric == "shipping":
        s = g["shipping_cost"].mean()
    elif metric == "avg_discount":
        s = g["discount"].mean() * 100
    else:
        s = g["is_loss"].mean() * 100
    s = _clean(s)
    if sort == "desc":
        s = s.sort_values(ascending=False)
    elif sort == "asc":
        s = s.sort_values()
    if top:
        s = s.head(top)
    labels = [f"{round(x * 100)}%" for x in s.index] if dim == "discount" else s.index.astype(str).tolist()
    additive = metric in ("orders", "revenue", "profit", "units")
    total = float(s.sum()) if additive else 0
    share = [round(100 * v / total, 1) if total else 0 for v in s.tolist()] if additive else None
    label, _, fm = METRICS[metric]
    return {"labels": labels, "values": s.round(2).tolist(), "share": share, "metric_label": label,
            "fmt": fm, "dim_label": DIMS[dim]}

# ------------------------------------------------------------------ compare
COMPARE_DIMS = ["region", "country", "category", "sub_category", "year", "customer_segment",
                "shipping_method", "payment_method", "customer_gender"]

def compare_options(base):
    return {k: sorted(base[k].astype(str).unique().tolist()) for k in COMPARE_DIMS if k in base.columns}

def compare(d, d_all, dim, a, b):
    metric = "revenue" if "revenue" in d else "order_id"
    def side(v):
        sd, sa = d[d[dim].astype(str) == v], d_all[d_all[dim].astype(str) == v]
        return sd, {"name": v, "kpis": build_kpis(sd, sa)}
    (da, ka), (db, kb) = side(a), side(b)
    key = "month" if dim == "year" else "year_month"
    xs = list(range(1, 13)) if dim == "year" else sorted(d[key].unique().tolist())
    def series(sd):
        s = sd.groupby(key)[metric].sum() if metric == "revenue" else sd.groupby(key).size()
        return s.reindex(xs, fill_value=0).round(2).tolist()
    mix = "sub_category" if dim == "category" else "category"
    mixlabels = sorted(d[mix].unique().tolist()) if mix in d else []
    def mixvals(sd):
        if not mixlabels:
            return []
        s = sd.groupby(mix)[metric].sum() if metric == "revenue" else sd.groupby(mix).size()
        s = s.reindex(mixlabels, fill_value=0)
        return (s / s.sum() * 100).round(1).tolist() if s.sum() else [0] * len(mixlabels)
    return {"dim": dim, "a": ka, "b": kb, "x": [str(x) for x in xs], "metric": "Revenue" if metric == "revenue" else "Orders",
            "fmt": "money" if metric == "revenue" else "count", "sa": series(da), "sb": series(db),
            "mix": {"dim": DIMS.get(mix, mix), "labels": mixlabels, "a": mixvals(da), "b": mixvals(db)}}

# ------------------------------------------------------------------ insights (the data analysis)
def _bars(s, f=lambda v: round(float(v), 1), n=6):
    return [{"label": str(i), "value": f(v)} for i, v in list(s.items())[:n]]

def _ins_discount(d, net):
    if not {"discount", "profit_margin_pct", "is_loss"} <= set(d.columns):
        return None
    m = d.groupby("discount")["profit_margin_pct"].mean()
    deep, shallow = d[d["discount"] >= 0.3], d[d["discount"] < 0.3]
    if deep.empty or shallow.empty:
        return None
    return dict(id="discount", tone="bad", title="Deep discounts destroy margin",
                text=f"Average margin falls from {m.iloc[0]:.1f}% at {m.index[0]:.0%} discount to {m.iloc[-1]:.1f}% at "
                     f"{m.index[-1]:.0%}. {deep['is_loss'].mean():.0%} of orders discounted 30% or more lose money, "
                     f"against {shallow['is_loss'].mean():.1%} of orders below 30%.",
                stat={"label": "Orders losing money", "value": f"{d['is_loss'].mean():.1%}"}, fmt="pct", signed=True,
                bars=[{"label": f"{x:.0%}", "value": round(float(v), 1)} for x, v in m.items()])

def _ins_concentration(d, net):
    if not {"profit", "category"} <= set(d.columns):
        return None
    p = net.groupby("category")["profit"].sum().sort_values(ascending=False)
    if p.sum() <= 0:
        return None
    sh = p / p.sum() * 100
    return dict(id="profit", tone="info", title="Profit is concentrated in one category",
                text=f"{p.index[0]} generates {sh.iloc[0]:.0f}% of net profit ({fmt(p.iloc[0])} of {fmt(p.sum())}). "
                     f"The other {len(p) - 1} categories together contribute {100 - sh.iloc[0]:.0f}%.",
                stat={"label": f"{p.index[0]} share", "value": f"{sh.iloc[0]:.0f}%"}, fmt="pct", bars=_bars(sh))

def _ins_returns(d, net):
    if not {"order_status", "category"} <= set(d.columns):
        return None
    r = (d["order_status"] == "Returned").groupby(d["category"]).mean().sort_values(ascending=False) * 100
    return dict(id="returns", tone="warn", title="Returns hit every category",
                text=f"{r.index[0]} has the highest return rate ({r.iloc[0]:.1f}%) and {r.index[-1]} the lowest "
                     f"({r.iloc[-1]:.1f}%). Overall {(d['order_status'] == 'Returned').mean():.1%} of orders are returned "
                     f"and {(d['order_status'] == 'Cancelled').mean():.1%} are cancelled.",
                stat={"label": "Return rate", "value": f"{(d['order_status'] == 'Returned').mean():.1%}"},
                fmt="pct", bars=_bars(r))

def _ins_risk(d, net):
    if "revenue" not in d:
        return None
    lost, gross = d[~d["order_status"].isin(NET)]["revenue"].sum(), d["revenue"].sum()
    if gross <= 0:
        return None
    return dict(id="risk", tone="warn", title="Revenue at risk in cancelled and returned orders",
                text=f"{fmt(lost)} of revenue ({lost / gross:.0%} of the gross {fmt(gross)}) sits in cancelled or "
                     f"returned orders, which is why every dashboard defaults to net revenue.",
                stat={"label": "Gross to net gap", "value": f"{lost / gross:.0%}"}, fmt="money",
                bars=[{"label": "Net", "value": round(float(gross - lost))}, {"label": "Cancelled / returned", "value": round(float(lost))}])

def _ins_geo(d, net):
    if not {"revenue", "region", "country"} <= set(d.columns):
        return None
    reg = net.groupby("region")["revenue"].sum().sort_values(ascending=False)
    cty = net.groupby("country")["revenue"].sum().sort_values(ascending=False)
    if len(reg) > 1:
        text = (f"{reg.index[0]} leads on net revenue ({fmt(reg.iloc[0])}) and {reg.index[-1]} trails "
                f"({fmt(reg.iloc[-1])}); the gap is only {reg.iloc[0] / reg.iloc[-1] - 1:.0%}, so regions are evenly "
                f"balanced. Best country overall: {cty.index[0]} ({fmt(cty.iloc[0])}).")
        bars, stat = _bars(reg, lambda v: round(float(v))), {"label": "Best region", "value": reg.index[0]}
    else:
        text = f"Within {reg.index[0]}, {cty.index[0]} is the top country with {fmt(cty.iloc[0])} net revenue."
        bars, stat = _bars(cty, lambda v: round(float(v))), {"label": "Top country", "value": cty.index[0]}
    return dict(id="geo", tone="good", title="Regions are evenly balanced", text=text, stat=stat, fmt="money", bars=bars)

def _ins_loss(d, net):
    if not {"is_loss", "sub_category"} <= set(d.columns):
        return None
    r = d.groupby("sub_category")["is_loss"].mean().sort_values(ascending=False) * 100
    return dict(id="loss", tone="warn", title="Where loss-making orders cluster",
                text=f"Loss-making orders are most common in {r.index[0]} ({r.iloc[0]:.1f}% of its orders) and least "
                     f"common in {r.index[-1]} ({r.iloc[-1]:.1f}%).",
                stat={"label": "Worst sub-category", "value": r.index[0]}, fmt="pct", bars=_bars(r))

def _ins_ship(d, net):
    if not {"shipping_cost", "shipping_method", "shipping_days"} <= set(d.columns):
        return None
    g = d.groupby("shipping_method").agg(cost=("shipping_cost", "mean"), days=("shipping_days", "mean"))
    same = g["days"].max() - g["days"].min() < 1.0
    text = (f"Shipping cost runs from {g['cost'].min():.1f} ({g['cost'].idxmin()}) to {g['cost'].max():.1f} "
            f"({g['cost'].idxmax()}) per order, yet average delivery time is {g['days'].min():.1f} to "
            f"{g['days'].max():.1f} days.")
    if same:
        text += " Faster methods do not deliver faster in this data, so treat delivery-speed claims with caution."
    return dict(id="ship", tone="warn" if same else "info", title="Pricier shipping is not faster shipping",
                text=text, stat={"label": "Delivery spread", "value": f"{g['days'].max() - g['days'].min():.1f} days"},
                fmt="money", bars=_bars(g["cost"].sort_values(ascending=False)))

def _ins_segment(d, net):
    if not {"revenue", "customer_segment"} <= set(d.columns):
        return None
    a = net.groupby("customer_segment")["revenue"].mean().sort_values(ascending=False)
    tot = net.groupby("customer_segment")["revenue"].sum().sort_values(ascending=False)
    return dict(id="segment", tone="info", title="Order value by customer segment",
                text=f"{a.index[0]} customers have the highest average order value ({a.iloc[0]:,.0f}) and {a.index[-1]} "
                     f"the lowest ({a.iloc[-1]:,.0f}). {tot.index[0]} brings the most revenue ({tot.iloc[0] / tot.sum():.0%}).",
                stat={"label": "Top AOV", "value": a.index[0]}, fmt="money", bars=_bars(a, lambda v: round(float(v))))

def _ins_products(d, net):
    if not {"revenue", "product_name"} <= set(d.columns):
        return None
    p = net.groupby("product_name")["revenue"].sum().sort_values(ascending=False)
    return dict(id="product", tone="good", title="A few products carry the revenue",
                text=f"The top 5 products make {p.head(5).sum() / p.sum():.0%} of net revenue; {p.index[0]} alone "
                     f"brings {fmt(p.iloc[0])}.",
                stat={"label": "Top product", "value": p.index[0]}, fmt="money", bars=_bars(p, lambda v: round(float(v)), 5))

def _ins_time(d, net):
    m = d.groupby("year_month").size()
    if len(m) < 6 or m.iloc[-1] >= 0.25 * m.max():
        return None
    y = d.groupby("year").size()
    return dict(id="time", tone="info", title="Order volume tails off in the last months",
                text=f"Orders peak in {m.idxmax()} ({m.max()} orders) and fall to {m.iloc[-1]} in {m.index[-1]}. "
                     f"This looks like an artefact of how the sample was generated, so avoid reading it as a business decline.",
                stat={"label": "Last month orders", "value": str(int(m.iloc[-1]))}, fmt="count",
                bars=[{"label": str(i), "value": int(v)} for i, v in y.items()])

INSIGHTS = [_ins_discount, _ins_concentration, _ins_returns, _ins_risk, _ins_geo, _ins_loss,
            _ins_ship, _ins_segment, _ins_products, _ins_time]

def build_insights(d):
    net = d[d["order_status"].isin(NET)]
    out = []
    for fn in INSIGHTS:
        try:
            r = fn(d, net)
        except Exception:
            r = None
        if r:
            out.append(r)
    return out

DATA_NOTES = [
    "Net revenue = Delivered + Processing orders. Cancelled and Returned orders still carry revenue in the source file.",
    "Profit = Revenue - Cost. Shipping cost is not deducted in the source data.",
    "Margin % on dashboards is total profit / total revenue (weighted), not the average of row margins.",
    "Customer IDs repeat but the same ID can have different segments, genders and regions, so customer-level analysis is approximate.",
    "Currency is not stated in the dataset, so amounts are shown without a symbol.",
]

# ------------------------------------------------------------------ table
def table_page(d, page, size, search, sort, direction):
    if search:
        s = search.lower()
        mask = (d["order_id"].str.lower().str.contains(s, regex=False)
                | d["product_name"].str.lower().str.contains(s, regex=False)
                | d["country"].str.lower().str.contains(s, regex=False))
        d = d[mask]
    if sort in d.columns:
        d = d.sort_values(sort, ascending=(direction != "desc"), kind="mergesort")
    total = len(d)
    return d.iloc[page * size:(page + 1) * size], total

def access_info(user, d):
    cfg = ROLES[user["role"]]
    return {"role": user["role"], "label": cfg["label"], "desc": cfg["desc"], "scope_col": cfg["row_scope"],
            "scope": user.get("scope"), "rows_visible": int(len(d)), "rows_total": int(len(DF)),
            "visible": [c for c in DF.columns if c not in cfg["hide"]],
            "hidden": [c for c in DF.columns if c in cfg["hide"]],
            "matrix": [{"role": r, "label": v["label"], "desc": v["desc"], "row_scope": v["row_scope"],
                        "hidden": len(v["hide"])} for r, v in ROLES.items()]}
