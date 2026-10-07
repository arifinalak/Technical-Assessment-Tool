import csv, io, json, sqlite3, datetime, jwt
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from werkzeug.security import check_password_hash
import core, rag

SECRET = "demo-secret-change-me-to-a-secure-32-byte-key"
app = FastAPI(title="Technical Assessment Tool")

def now():
    return datetime.datetime.now(datetime.timezone.utc)

def audit(username, role, action, detail=""):
    con = sqlite3.connect("auth.db")
    con.execute("CREATE TABLE IF NOT EXISTS audit(ts TEXT, username TEXT, role TEXT, action TEXT, detail TEXT)")
    con.execute("INSERT INTO audit VALUES(?,?,?,?,?)",
                (now().strftime("%Y-%m-%d %H:%M:%S"), username, role, action, str(detail)[:200]))
    con.commit(); con.close()

class Login(BaseModel):
    username: str
    password: str

class Chat(BaseModel):
    question: str = ""
    preset: str = ""

@app.post("/login")
def login(b: Login):
    con = sqlite3.connect("auth.db")
    row = con.execute("SELECT pw, role, scope FROM users WHERE username=?", (b.username,)).fetchone()
    con.close()
    if not row or not check_password_hash(row[0], b.password):
        audit(b.username[:40], "-", "login_failed")
        raise HTTPException(401, "Invalid username or password")
    tok = jwt.encode({"u": b.username, "role": row[1], "scope": row[2], "exp": now() + datetime.timedelta(hours=8)},
                     SECRET, algorithm="HS256")
    audit(b.username, row[1], "login")
    return {"token": tok, "username": b.username, "role": row[1], "scope": row[2]}

def current_user(authorization: str = Header(default="")):
    try:
        return jwt.decode(authorization.replace("Bearer ", ""), SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")

def net_filters(year: str = "", category: str = "", region: str = "", segment: str = "",
                status: str = "Delivered,Processing"):
    return dict(year=year, category=category, region=region, segment=segment, status=status)

def any_filters(year: str = "", category: str = "", region: str = "", segment: str = "", status: str = ""):
    return dict(year=year, category=category, region=region, segment=segment, status=status)

def pair(user, f):
    base = core.scoped(user)
    f_all = {**f, "status": ""}
    return core.apply_filters(base, **f), core.apply_filters(base, **f_all)

@app.get("/api/me")
def me(user=Depends(current_user)):
    return core.access_info(user, core.scoped(user)) | {"username": user["u"]}

@app.get("/api/meta")
def meta(user=Depends(current_user)):
    d = core.scoped(user)
    cols = set(d.columns)
    return {"years": sorted(int(y) for y in d["year"].unique()),
            "categories": sorted(d["category"].unique().tolist()),
            "regions": sorted(d["region"].unique().tolist()),
            "segments": sorted(d["customer_segment"].unique().tolist()),
            "dims": core.available_dims(cols), "metrics": core.available_metrics(cols),
            "compare": core.compare_options(d)}

@app.get("/api/health")
def health():
    return rag.health()

@app.get("/api/dashboard")
def dashboard(user=Depends(current_user), f=Depends(net_filters)):
    d, d_all = pair(user, f)
    return {"kpis": core.build_kpis(d, d_all), "spark": core.build_spark(d),
            "charts": core.build_charts(d, d_all), "heatmap": core.build_heatmap(d), "rows": int(len(d))}

@app.get("/api/explore")
def explore(dim: str, metric: str, top: int = 0, sort: str = "desc", user=Depends(current_user),
            f=Depends(net_filters)):
    d, _ = pair(user, f)
    if dim not in core.DIMS or dim not in d.columns:
        raise HTTPException(400, "Unknown or hidden dimension")
    if metric not in core.METRICS or not core.METRICS[metric][1] <= set(d.columns):
        raise HTTPException(403, "Metric not available for your role")
    return core.explore(d, dim, metric, top, sort if sort in ("desc", "asc", "natural") else "desc")

@app.get("/api/compare")
def compare(dim: str, a: str, b: str, user=Depends(current_user), f=Depends(net_filters)):
    d, d_all = pair(user, f)
    if dim not in core.COMPARE_DIMS or dim not in d.columns:
        raise HTTPException(400, "Cannot compare on that dimension")
    return core.compare(d, d_all, dim, a, b)

@app.get("/api/insights")
def insights(user=Depends(current_user), f=Depends(any_filters)):
    _, d_all = pair(user, f)
    return {"insights": core.build_insights(d_all), "notes": core.DATA_NOTES, "rows": int(len(d_all))}

def _filtered(user, f):
    d = core.apply_filters(core.scoped(user), **f)
    return d

@app.get("/api/table")
def table(user=Depends(current_user), f=Depends(any_filters), page: int = 0, size: int = 15,
          search: str = "", sort: str = "", dir: str = "desc"):
    part, total = core.table_page(_filtered(user, f), max(page, 0), min(max(size, 5), 100), search[:60], sort, dir)
    js = json.loads(part.to_json(orient="split"))
    return {"total": total, "cols": js["columns"], "rows": js["data"], "page": page, "size": size}

@app.get("/api/export")
def export(user=Depends(current_user), f=Depends(any_filters), search: str = ""):
    d, total = core.table_page(_filtered(user, f), 0, 10**6, search[:60], "", "desc")
    buf = io.StringIO()
    d.to_csv(buf, index=False)
    audit(user["u"], user["role"], "export_csv", f"{total} rows")
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=orders_export.csv"})

@app.get("/api/chat/presets")
def presets(user=Depends(current_user)):
    return rag.presets_for(user)

@app.post("/api/chat")
def chat(b: Chat, user=Depends(current_user)):
    q = b.question.strip()[:400]
    if not q and not b.preset:
        raise HTTPException(400, "Empty question")
    out = rag.answer(q, user, b.preset or None)
    audit(user["u"], user["role"], "chat", b.preset or q)
    return out

@app.get("/api/access")
def access(user=Depends(current_user)):
    info = core.access_info(user, core.scoped(user))
    if user["role"] == "admin":
        con = sqlite3.connect("auth.db")
        info["users"] = [dict(zip(("username", "role", "scope"), r)) for r in
                         con.execute("SELECT username, role, scope FROM users ORDER BY rowid")]
        info["audit"] = [dict(zip(("ts", "username", "role", "action", "detail"), r)) for r in
                         con.execute("SELECT ts, username, role, action, detail FROM audit ORDER BY rowid DESC LIMIT 40")]
        con.close()
    return info

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html", headers={"Cache-Control": "no-store"})
