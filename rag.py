"""Chat: text-to-SQL on the user's permitted data + role-filtered vector search over summaries."""
import os, re, sqlite3, time, requests
import core
from google import genai

BACKEND = os.getenv("LLM_BACKEND", "ollama")        # "ollama" (local) or "cloud" (free tier)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
_state = {}

class LLMDown(Exception):
    pass

def _vec():   # lazy: heavy libraries load only when the vector path is used
    if not _state:
        from fastembed import TextEmbedding
        import chromadb
        _state["emb"] = TextEmbedding("BAAI/bge-small-en-v1.5")
        _state["db"] = chromadb.PersistentClient("chroma_db")
    return _state

def embed(texts):
    return [v.tolist() for v in _vec()["emb"].embed(texts)]

def health():
    if BACKEND == "cloud":
        return {"online": True, "model": os.getenv("CLOUD_MODEL", "cloud"), "backend": "cloud", "ready": True}
    try:
        names = [m["name"] for m in requests.get(OLLAMA_URL + "/api/tags", timeout=1.5).json().get("models", [])]
        ready = any(n == OLLAMA_MODEL or n.split(":")[0] == OLLAMA_MODEL.split(":")[0] and OLLAMA_MODEL in n
                    for n in names)
        return {"online": True, "model": OLLAMA_MODEL, "backend": "ollama", "ready": ready}
    except Exception:
        return {"online": False, "model": OLLAMA_MODEL, "backend": "ollama", "ready": False}

def llm(prompt):
    try:
        if BACKEND == "cloud":    # any OpenAI-compatible free tier (Groq, OpenRouter, ...)
            r = requests.post(os.environ["CLOUD_URL"], timeout=60,
                              headers={"Authorization": "Bearer " + os.environ["CLOUD_KEY"]},
                              json={"model": os.environ["CLOUD_MODEL"], "temperature": 0,
                                    "messages": [{"role": "user", "content": prompt}]})
            return r.json()["choices"][0]["message"]["content"].strip()
        r = requests.post(OLLAMA_URL + "/api/generate", timeout=180,
                          json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "keep_alive": "30m",
                                "options": {"temperature": 0, "num_ctx": 2048}})
        return r.json()["response"].strip()
    except (requests.RequestException, KeyError, ValueError, TypeError) as e:
        raise LLMDown(str(e))

# ---------------- indexing (run once: python build_index.py) ----------------
def build_index():
    df, docs, metas = core.DF, [], []
    def add(text, region, tier):
        docs.append(text)
        metas.append({"region": region, "tier": tier})
    # business definitions: no numbers, so they are safe for every role
    add("Revenue = unit_price x quantity x (1 - discount). Net revenue excludes "
        "Cancelled and Returned orders.", "ALL", "sales")
    add("Profit = revenue - cost. Shipping cost is not deducted. "
        "Margin % = profit / revenue x 100.", "ALL", "finance")
    add("Order status values: Delivered, Processing, Returned, Cancelled. "
        "Return rate = Returned orders / all orders.", "ALL", "ops")
    add("Discount levels run from 0 to 50 percent. High discounts push margin "
        "negative.", "ALL", "finance")
    for (reg, cat, yr), g in df.groupby(["region", "category", "year"]):
        ok = g[g["order_status"].isin(core.NET)]
        rev, prof = ok["revenue"].sum(), ok["profit"].sum()
        tag = f"{reg} / {cat} / {yr}"
        add(f"{tag}: {len(g)} orders; status counts {g['order_status'].value_counts().to_dict()}; "
            f"average shipping cost {g['shipping_cost'].mean():.2f}.", reg, "ops")
        add(f"{tag}: net revenue {rev:.0f}; average discount "
            f"{100 * g['discount'].mean():.1f}%.", reg, "sales")
        add(f"{tag}: net profit {prof:.0f}; margin {100 * prof / max(rev, 1):.1f}%.", reg, "finance")
    db = _vec()["db"]
    try:
        db.delete_collection("sales")
    except Exception:
        pass
    col = db.create_collection("sales")
    col.add(documents=docs, embeddings=embed(docs), metadatas=metas, ids=[f"c{i}" for i in range(len(docs))])
    print("indexed", len(docs), "chunks")

# ---------------- vector path ----------------
def role_filter(user):
    cfg = core.ROLES[user["role"]]
    conds = [{"tier": {"$in": cfg["tiers"]}}]
    if cfg["row_scope"] == "region":
        conds.append({"region": {"$in": [user["scope"], "ALL"]}})
    return conds[0] if len(conds) == 1 else {"$and": conds}

def vector_answer(question, user):
    col = _vec()["db"].get_collection("sales")
    res = col.query(query_embeddings=embed([question]), n_results=5, where=role_filter(user))
    ctx = res["documents"][0]
    text = llm("Answer ONLY from the context. If it is not there, say you do not know. Be concise.\n"
               "Context:\n- " + "\n- ".join(ctx) + "\nQuestion: " + question)
    return {"answer": text, "sources": ctx}

# ---------------- SQL path ----------------
RULES = ("You write one SQLite SELECT query for the table below.\n"
         "Rules: return only the SQL, no explanation, no semicolon.\n"
         "For revenue or profit questions exclude order_status IN ('Cancelled','Returned') "
         "unless the user asks about them.\n"
         "For questions predicting or forecasting future years like 2025 or 2026, query those years directly.\n"
         "If the question asks for a definition or cannot be answered from the table, "
         "return exactly: NONE\n")
NETSQL = "order_status NOT IN ('Cancelled','Returned')"
EXAMPLES = [  # (columns needed, question, SQL) - only shown if the role can see the columns
    (set(), "Hi", "NONE"),
    (set(), "Hello", "NONE"),
    ({"revenue", "year"}, "Predict our revenue in 2025.",
     f"SELECT SUM(revenue) FROM sales WHERE year = 2025 AND {NETSQL}"),
    ({"revenue", "category"}, "Which category has the highest revenue?",
     f"SELECT category, SUM(revenue) AS r FROM sales WHERE {NETSQL} GROUP BY category ORDER BY r DESC LIMIT 1"),
    ({"revenue", "year"}, "What was total revenue in 2023?",
     f"SELECT SUM(revenue) FROM sales WHERE year = 2023 AND {NETSQL}"),
    ({"order_status"}, "What is the return rate?",
     "SELECT ROUND(100.0 * SUM(order_status = 'Returned') / COUNT(*), 1) FROM sales"),
    ({"profit_margin_pct", "discount"}, "Average margin by discount level?",
     "SELECT discount, ROUND(AVG(profit_margin_pct), 1) FROM sales GROUP BY discount ORDER BY discount"),
    ({"shipping_cost", "shipping_method"}, "Average shipping cost per method?",
     "SELECT shipping_method, ROUND(AVG(shipping_cost), 2) FROM sales GROUP BY shipping_method"),
]

# one-click questions: fixed, reliable SQL (the model only phrases the result)
PRESETS = [
    ("top_cat", "Which categories earn the most net revenue?", {"revenue", "category"},
     f"SELECT category, ROUND(SUM(revenue)) AS net_revenue FROM sales WHERE {NETSQL} GROUP BY category ORDER BY 2 DESC"),
    ("top_prod", "Top 5 products by net revenue", {"revenue", "product_name"},
     f"SELECT product_name, ROUND(SUM(revenue)) AS net_revenue FROM sales WHERE {NETSQL} GROUP BY 1 ORDER BY 2 DESC LIMIT 5"),
    ("top_country", "Which countries sell the most?", {"revenue", "country"},
     f"SELECT country, ROUND(SUM(revenue)) AS net_revenue FROM sales WHERE {NETSQL} GROUP BY 1 ORDER BY 2 DESC LIMIT 6"),
    ("by_year", "How does net revenue change by year?", {"revenue", "year"},
     f"SELECT year, ROUND(SUM(revenue)) AS net_revenue FROM sales WHERE {NETSQL} GROUP BY 1 ORDER BY 1"),
    ("margin_disc", "How does margin change with discount level?", {"profit_margin_pct", "discount"},
     "SELECT ROUND(discount * 100) AS discount_pct, ROUND(AVG(profit_margin_pct), 1) AS avg_margin_pct FROM sales GROUP BY discount ORDER BY discount"),
    ("loss_sub", "Which sub-categories lose money most often?", {"is_loss", "sub_category"},
     "SELECT sub_category, ROUND(100.0 * AVG(is_loss), 1) AS loss_orders_pct FROM sales GROUP BY 1 ORDER BY 2 DESC LIMIT 6"),
    ("return_cat", "Return rate by category", {"order_status", "category"},
     "SELECT category, ROUND(100.0 * SUM(order_status = 'Returned') / COUNT(*), 1) AS return_rate_pct FROM sales GROUP BY 1 ORDER BY 2 DESC"),
    ("status", "Break down orders by status", {"order_status"},
     "SELECT order_status, COUNT(*) AS orders FROM sales GROUP BY 1 ORDER BY 2 DESC"),
    ("ship", "Average shipping cost by method", {"shipping_cost", "shipping_method"},
     "SELECT shipping_method, ROUND(AVG(shipping_cost), 2) AS avg_shipping_cost FROM sales GROUP BY 1 ORDER BY 2 DESC"),
    ("seg_aov", "Average order value by customer segment", {"revenue", "customer_segment"},
     f"SELECT customer_segment, ROUND(AVG(revenue), 2) AS avg_order_value FROM sales WHERE {NETSQL} GROUP BY 1 ORDER BY 2 DESC"),
]

def presets_for(user):
    cols = set(core.scoped(user).columns)
    return [{"id": i, "label": label} for i, label, need, _ in PRESETS if need <= cols][:3]

BLOCK = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|pragma|replace)\b", re.I)

def schema_text(d):
    kinds = {"f": "REAL", "i": "INTEGER"}
    cols = ", ".join(f"{c} {kinds.get(d[c].dtype.kind, 'TEXT')}" for c in d.columns)
    return f"Table sales({cols})"

def clean_sql(t):
    t = t.replace("```sql", "").replace("```", "").strip()
    return t.split(";")[0].strip()

def safe(sql):
    return sql.lower().startswith("select") and not BLOCK.search(sql)

def _table(cur, rows):
    return {"cols": [c[0] for c in cur.description], "rows": [list(r) for r in rows]}

def _phrase(question, table):
    try:
        return llm(f"Question: {question}\nColumns: {table['cols']}\nRows: {table['rows']}\n"
                   "Answer in one or two sentences using ONLY these rows.")
    except LLMDown:
        return f"Here are the results ({len(table['rows'])} rows). The AI model is offline, so I could not summarise them."

import difflib

def answer(question, user, preset=None):
    t0 = time.time()
    d = core.scoped(user)
    con = sqlite3.connect(":memory:")
    d.to_sql("sales", con, index=False)     # holds ONLY what this user may see
    def done(out):
        out["ms"] = int((time.time() - t0) * 1000)
        return out
    
    q_lower = question.strip().lower().strip(".!?")
    greetings = ["hi", "hello", "hey", "how are you", "who are you", "how are you doing", "what is up", "whats up"]
    if difflib.get_close_matches(q_lower, greetings, n=1, cutoff=0.7):
        return done({"answer": "Hello! I am your AI sales assistant. I can help you query data and find insights. Try asking a question about revenue, margins, or products!", "source": "greeting"})

    if preset:
        hit = next((p for p in PRESETS if p[0] == preset and p[2] <= set(d.columns)), None)
        if not hit:
            return done({"answer": "That question is not available for your role.", "source": "denied"})
        cur = con.execute(hit[3]); table = _table(cur, cur.fetchall())
        return done({"answer": _phrase(hit[1], table), "sql": hit[3], "table": table, "source": "sql"})
    shots = "\n".join(f"Q: {q}\nSQL: {s}" for need, q, s in EXAMPLES if need <= set(d.columns))
    try:
        sql = clean_sql(llm(RULES + schema_text(d) + "\n\n" + shots + f"\n\nQ: {question}\nSQL:"))
    except LLMDown:
        return done({"answer": "The AI model is not running, so I cannot answer free-text questions right now. "
                               "Start Ollama, or use one of the quick questions, which work without it.",
                     "source": "offline", "offline": True})
    if safe(sql):
        try:
            cur = con.execute(sql); rows = cur.fetchmany(30)
            if rows:
                table = _table(cur, rows)
                return done({"answer": _phrase(question, table), "sql": sql, "table": table, "source": "sql"})
        except sqlite3.Error:
            pass
    try:
        out = vector_answer(question, user)
        lower_ans = out["answer"].lower()
        if "do not know" in lower_ans or "don't know" in lower_ans or "not there" in lower_ans:
            api_key = os.environ.get("GEMINI_API_KEY", "")
            if api_key:
                try:
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model='gemini-3.8-flash',
                        contents=f"You are a helpful business assistant. Answer the following question: {question}"
                    )
                    out["answer"] = response.text
                    out["source"] = "gemini api"
                except Exception:
                    out["answer"] = "I'm currently un-available please try again."
            else:
                out["answer"] = "I'm currently un-available please try again."
        else:
            out["source"] = "vector"
        return done(out)
    except LLMDown:
        return done({"answer": "The AI model went offline while answering.", "source": "offline", "offline": True})
    except Exception:
        return done({"answer": "I could not search the data summaries. Run build_index.py once (it needs "
                               "internet the first time), then try again.", "source": "error"})
