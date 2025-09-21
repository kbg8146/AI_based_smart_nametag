# nfc_server.py  (추천 산업군 표시 개선본)
from fastapi import FastAPI, Request, HTTPException, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import os, re, unicodedata, secrets, string, time
from datetime import datetime, timezone
from urllib.parse import quote, unquote

import gspread
import pandas as pd

# ===== FastAPI & CORS =====
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # 운영 시 특정 도메인으로 제한 권장
    allow_methods=["GET","POST","OPTIONS"],
    allow_headers=["*"],
)

# ===== 환경 설정 =====
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE", r"C:\keys\sa.json")
ADMIN_KEY = os.getenv("ADMIN_KEY", "set-your-admin-key")

SPREAD_URL   = "https://docs.google.com/spreadsheets/d/1kkt336f1G-XqfDuwCUOnqpKlxTcnwLQy-XS4SQv6lM0/edit"
RESP_WS_NAME = "설문지 응답 시트"
CLU_WS_NAME  = "Clustered Result with Distance"

# ===== gspread 연결 =====
gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
sh = gc.open_by_url(SPREAD_URL)
ws_responses = sh.worksheet(RESP_WS_NAME)
ws_cluster   = sh.worksheet(CLU_WS_NAME)

# ===== 유틸 =====
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s))
    s = s.replace("\u00A0"," ").replace("\u200b","").replace("\ufeff","")
    s = re.sub(r"\s+","", s)
    return s.lower().strip()

def _read_ws(ws) -> pd.DataFrame:
    df = pd.DataFrame(ws.get_all_records())
    df.columns = [c.strip() for c in df.columns]
    return df

def _find_col(df: pd.DataFrame, candidates) -> str | None:
    m = {_norm(c): c for c in df.columns}
    for cand in candidates:
        k = _norm(cand)
        if k in m:
            return m[k]
    # fallback: 이름(비슷어) 휴리스틱
    for k, orig in m.items():
        if any(tag in k for tag in ["이름","성명","name","fullname"]):
            return orig
    return None

def _gen_token(length=8, alphabet=string.ascii_letters + string.digits):
    return "".join(secrets.choice(alphabet) for _ in range(length))

def _col_letter(idx: int) -> str:
    letters = ""
    while idx:
        idx, rem = divmod(idx-1, 26)
        letters = chr(65+rem) + letters
    return letters

def _ensure_cols(ws, header_row, needed_names):
    """needed_names 컬럼을 헤더에 보장하고 1-based 인덱스 dict 반환"""
    header = header_row[:]
    changed = False
    for name in needed_names:
        if name not in header:
            header.append(name)
            changed = True
    if changed:
        ws.update("1:1", [header])
    return {name: header.index(name)+1 for name in needed_names}

def _construct_profile_url(request_base_url: str, token: str):
    base = str(request_base_url)
    if not base.endswith("/"):
        base += "/"
    return f"{base}u/{token}"

def _normalize_uid(uid: str) -> str:
    s = re.sub(r"[^0-9a-fA-F]","", uid or "")
    return s.upper()

# ===== 토큰 인덱스 캐시 (touch 성능용) =====
_INDEX_TTL = int(os.getenv("INDEX_TTL", "60"))  # seconds
_INDEX_CACHE = {"exp": 0, "token_map": {}, "header": []}

def _ensure_token_index(ws):
    now = time.time()
    if now < _INDEX_CACHE["exp"]:
        return _INDEX_CACHE["header"], _INDEX_CACHE["token_map"]

    vals = ws.get_all_values()
    if not vals:
        return [], {}
    header = [h.strip() for h in vals[0]]

    # token 우선, 그다음 Token/토큰도 허용
    tok_col_name = None
    for cand in ["token","Token","토큰"]:
        if cand in header:
            tok_col_name = cand; break

    token_map = {}
    if tok_col_name:
        tok_idx = header.index(tok_col_name) + 1
        for i, row in enumerate(vals[1:], start=2):
            if len(row) >= tok_idx:
                t = (row[tok_idx-1] or "").strip()
                if t:
                    token_map[_norm(t)] = i

    _INDEX_CACHE.update({"exp": now + _INDEX_TTL, "token_map": token_map, "header": header})
    return header, token_map

def _ensure_token_column_and_fill(ws):
    """
    시트 전체를 1회 읽어 token 컬럼을 보장하고,
    모든 데이터 행(2~N)의 token 셀을 채움(비어있을 때 랜덤 생성).
    대량 쓰기는 컬럼 단위로 batch update.
    """
    values = ws.get_all_values()
    if not values:
        return {"created": 0, "col_name": None, "col_index": None, "sample": []}

    header = [h.strip() for h in values[0]]

    # token/Token/토큰 우선순위: token -> Token -> 토큰
    token_col_name = None
    for cand in ["token","Token","토큰"]:
        if cand in header:
            token_col_name = cand; break
    if token_col_name is None:
        header.append("token")
        ws.update("1:1", [header])
        token_col_name = "token"
        values[0] = header

    token_col_idx = header.index(token_col_name) + 1
    token_col_letter = _col_letter(token_col_idx)

    # 샘플 표시용 이름컬럼
    name_col_idx = None
    for cand in ["이름","성명","Name","Full Name","이름(실명)"]:
        if cand in header:
            name_col_idx = header.index(cand) + 1
            break

    # 기존 토큰 수집(중복 방지)
    existing = set()
    for r in range(1, len(values)):
        row = values[r]
        if len(row) >= token_col_idx:
            tok = (row[token_col_idx-1] or "").strip()
            if tok:
                existing.add(tok)

    # 채움 벡터 생성
    created, samples = 0, []
    out_col_values = []  # rows 2..N 에 대한 [[tok], [tok], ...]
    for r in range(1, len(values)):
        row = values[r]
        if len(row) < token_col_idx:
            row += [""] * (token_col_idx - len(row))
        tok = (row[token_col_idx-1] or "").strip()
        if not tok:
            t = _gen_token(8)
            while t in existing:
                t = _gen_token(8)
            tok = t
            existing.add(tok)
            created += 1
            if name_col_idx and name_col_idx <= len(row):
                samples.append({"row": r+1, "name": row[name_col_idx-1], "token": tok})
        out_col_values.append([tok])

    # 컬럼 범위 일괄 업데이트
    if out_col_values:
        start_row = 2
        CHUNK = 500
        for i in range(0, len(out_col_values), CHUNK):
            sub_values = out_col_values[i:i+CHUNK]
            sub_start = start_row + i
            sub_end = sub_start + len(sub_values) - 1
            rng = f"{token_col_letter}{sub_start}:{token_col_letter}{sub_end}"
            ws.update(rng, sub_values, value_input_option="RAW")

    return {"created": created, "col_name": token_col_name, "col_index": token_col_idx, "sample": samples}

# ===== 추천 산업군 선택 헬퍼 =====
def _pick_top_industries(df_clu: pd.DataFrame, clu_row: pd.Series) -> str:
    """
    우선순위:
    1) 라벨형 컬럼: 추천 산업군/Top Industries/추천 직무/top_industries/GroupName/Cluster/Subgroup
    2) 점수형 컬럼 3개(Embedded & Control, Semiconductor & Circuits, AI & Applications) 중 상위 1~2개
    """
    # 1) 라벨형 컬럼
    label_col = _find_col(df_clu, [
        "추천 산업군", "Top Industries", "추천 직무", "top_industries",
        "GroupName", "Cluster", "Subgroup"
    ])
    if label_col:
        v = str(clu_row.get(label_col, "")).strip()
        if v:
            return v

    # 2) 점수형 컬럼
    candidate_cols = ["Embedded & Control", "Semiconductor & Circuits", "AI & Applications"]
    have = [c for c in candidate_cols if c in df_clu.columns]
    scores = []
    for c in have:
        raw = str(clu_row.get(c, "")).strip()
        try:
            val = float(raw.replace(",", ""))
        except Exception:
            val = 0.0
        scores.append((val, c))
    scores.sort(key=lambda x: x[0], reverse=True)

    if not scores:
        return ""

    # 상위 2개까지만 노출
    names = [name for _, name in scores[:2]]
    # (선택) 한글 표시 원하면 여기서 매핑
    # kmap = {"Embedded & Control":"임베디드/제어","Semiconductor & Circuits":"반도체/회로","AI & Applications":"AI/응용"}
    # names = [kmap.get(n, n) for n in names]
    return ", ".join(names)

# ===== 라우트 =====
@app.get("/", response_class=HTMLResponse)
def root():
    return HTMLResponse('<h2>NFC Server</h2><p><a href="/users">/users</a></p>')

# 관리자 프로비저닝 UI (templates/provision.html 사용)
@app.get("/admin/provision", response_class=HTMLResponse)
def ui_provision(request: Request, key: str = Query(..., description="관리자 키")):
    if key != ADMIN_KEY:
        raise HTTPException(403, "forbidden")
    return templates.TemplateResponse("provision.html", {"request": request})

@app.get("/users", response_class=HTMLResponse)
def list_users():
    df = _read_ws(ws_responses)
    if df.empty:
        return HTMLResponse("<h2>응답 시트에 데이터가 없습니다.</h2>")

    name_col  = _find_col(df, ["이름","성명","Name","Full Name","이름(실명)"])
    token_col = _find_col(df, ["token","Token","토큰"])

    prefer = ["이름","성명","학교","학년","전공","이메일 주소","이메일",
              "Name","School","Year","Major","Email"]
    cols = [c for c in prefer if c in df.columns] or df.columns.tolist()

    df["_token_link"] = df[token_col].apply(
        lambda t: f'<a href="/u/{quote(str(t), safe="")}">토큰</a>'
        if token_col and pd.notna(t) and str(t).strip() else ""
    )
    df["_name_link"] = df[name_col].apply(
        lambda x: f'<a href="/user/{quote(str(x), safe="")}">프로필</a>'
        if name_col and pd.notna(x) else ""
    )

    return HTMLResponse(f"<h2>응답자 목록</h2>{df[cols+['_name_link','_token_link']].to_html(index=False, escape=False)}")

@app.get("/user/{name}", response_class=HTMLResponse)
def render_user_profile(request: Request, name: str):
    name = unquote(name)
    df_resp = _read_ws(ws_responses)
    df_clu  = _read_ws(ws_cluster)

    if df_resp.empty:
        raise HTTPException(500, "응답 시트에 데이터가 없습니다.")

    name_col_resp = _find_col(df_resp, ["이름","성명","Name","Full Name","이름(실명)"])
    if not name_col_resp:
        raise HTTPException(500, f"응답 시트 이름 컬럼 미발견: {df_resp.columns.tolist()}")

    df_resp["_name_norm"] = df_resp[name_col_resp].astype(str).apply(_norm)
    name_norm = _norm(name)

    match = df_resp[df_resp["_name_norm"] == name_norm]
    if match.empty:
        raise HTTPException(404, f"설문 응답에 '{name}' 없음")
    resp = match.iloc[0]

    # 토큰(있으면) 템플릿으로 전달
    token_col = _find_col(df_resp, ["token","Token","토큰"])
    user_token = str(resp.get(token_col, "")) if token_col else ""

    # 추천 산업군
    top_industries = ""
    if not df_clu.empty:
        name_col_clu = _find_col(df_clu, ["이름","성명","Name","Full Name","이름(실명)"])
        if name_col_clu:
            df_clu["_name_norm"] = df_clu[name_col_clu].astype(str).apply(_norm)
            clu_match = df_clu[df_clu["_name_norm"] == name_norm]
            if not clu_match.empty:
                clu = clu_match.iloc[0]
                top_industries = _pick_top_industries(df_clu, clu)

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": {
            "name":   resp.get(name_col_resp, ""),
            "school": resp.get("학교", resp.get("School", "")),
            "year":   resp.get("학년", resp.get("Year", "")),
            "major":  resp.get("전공", resp.get("Major", "")),
            "email":  resp.get("이메일 주소", resp.get("이메일", resp.get("Email", ""))),
            "top_industries": top_industries,
            "token": user_token,
        }
    })

@app.get("/u/{token}", response_class=HTMLResponse)
def profile_by_token(request: Request, token: str):
    token = unquote(token)
    df_resp = _read_ws(ws_responses)
    df_clu  = _read_ws(ws_cluster)

    if df_resp.empty:
        raise HTTPException(500, "응답 시트에 데이터가 없습니다.")

    token_col = _find_col(df_resp, ["token","Token","토큰"])
    if not token_col:
        raise HTTPException(404, "응답 시트에 token 컬럼이 없습니다. 먼저 토큰을 생성하세요.")

    df_resp["_tok_norm"] = df_resp[token_col].astype(str).apply(_norm)
    match = df_resp[df_resp["_tok_norm"] == _norm(token)]
    if match.empty:
        raise HTTPException(404, f"토큰 '{token}'에 해당하는 사용자가 없습니다.")
    row = match.iloc[0]

    name_col_resp = _find_col(df_resp, ["이름","성명","Name","Full Name","이름(실명)"])
    person_name = str(row.get(name_col_resp, ""))
    name_norm = _norm(person_name)

    # 추천 산업군
    top_industries = ""
    if not df_clu.empty:
        name_col_clu = _find_col(df_clu, ["이름","성명","Name","Full Name","이름(실명)"])
        if name_col_clu:
            df_clu["_name_norm"] = df_clu[name_col_clu].astype(str).apply(_norm)
            clu_match = df_clu[df_clu["_name_norm"] == name_norm]
            if not clu_match.empty:
                clu = clu_match.iloc[0]
                top_industries = _pick_top_industries(df_clu, clu)

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": {
            "name":   person_name,
            "school": row.get("학교", row.get("School", "")),
            "year":   row.get("학년", row.get("Year", "")),
            "major":  row.get("전공", row.get("Major", "")),
            "email":  row.get("이메일 주소", row.get("이메일", row.get("Email", ""))),
            "top_industries": top_industries,
            "token": token,
        }
    })

# ----- 프로비저닝: assign -----
@app.post("/admin/provision/assign")
def provision_assign(
    request: Request,
    key: str = Query(..., description="관리자 키"),
    payload: dict = Body(..., example={"uid": "04AABBCCDD", "base_url": ""})
):
    if key != ADMIN_KEY:
        raise HTTPException(403, "forbidden")

    uid = _normalize_uid(payload.get("uid", ""))
    if not uid:
        raise HTTPException(400, "uid is required")

    base_url = payload.get("base_url") or str(request.base_url)
    ws = ws_responses

    # 필요한 컬럼 보장
    col_uid = _ensure_cols(ws, ws.row_values(1), ["uid"])["uid"]
    header = [h.strip() for h in ws.row_values(1)]
    token_col_name = next((c for c in ("token","Token","토큰") if c in header), None)
    if not token_col_name:
        raise HTTPException(404, "token column missing. 먼저 /admin/generate-tokens 실행")
    col_token = header.index(token_col_name) + 1
    more = _ensure_cols(ws, header, ["url","assigned_at"])
    col_url, col_assigned_at = more["url"], more["assigned_at"]

    # 전체 읽기 1회
    matrix = ws.get_all_values()
    if not matrix:
        raise HTTPException(409, "no data")
    header = [h.strip() for h in matrix[0]]
    rows = matrix[1:]

    idx_uid = header.index("uid") if "uid" in header else None
    idx_token = header.index(token_col_name)

    def _safe(row, idx):
        return row[idx] if idx is not None and idx < len(row) else ""

    # 1) 같은 UID가 있으면 재사용
    reuse_row_1b, reuse_token = None, None
    if idx_uid is not None:
        for i, row in enumerate(rows, start=2):
            if (_safe(row, idx_uid) or "").strip().upper() == uid:
                reuse_row_1b = i
                reuse_token = (_safe(row, idx_token) or "").strip()
                break
    if reuse_row_1b and reuse_token:
        url = _construct_profile_url(base_url, reuse_token)
        now_iso = datetime.now(timezone.utc).isoformat()
        ws.batch_update([
            {"range": f"{_col_letter(col_url)}{reuse_row_1b}",         "values": [[url]]},
            {"range": f"{_col_letter(col_assigned_at)}{reuse_row_1b}", "values": [[now_iso]]},
        ])
        return {"status":"ok","uid":uid,"token":reuse_token,"url":url,"reused":True}

    # 2) 미사용 토큰(토큰O + uid 비어있음)
    candidate_row_1b, token_val = None, None
    for i, row in enumerate(rows, start=2):
        tok = (_safe(row, idx_token) or "").strip()
        u   = (_safe(row, idx_uid) or "").strip() if idx_uid is not None else ""
        if tok and not u:
            candidate_row_1b = i
            token_val = tok
            break
    if not candidate_row_1b:
        raise HTTPException(409, "no unused token available")

    # 3) 쓰기
    url = _construct_profile_url(base_url, token_val)
    now_iso = datetime.now(timezone.utc).isoformat()
    ws.batch_update([
        {"range": f"{_col_letter(col_uid)}{candidate_row_1b}",         "values": [[uid]]},
        {"range": f"{_col_letter(col_url)}{candidate_row_1b}",         "values": [[url]]},
        {"range": f"{_col_letter(col_assigned_at)}{candidate_row_1b}", "values": [[now_iso]]},
    ])
    return {"status":"ok","uid":uid,"token":token_val,"url":url,"reused":False}

# ----- 프로비저닝: remap -----
@app.post("/admin/provision/remap")
def provision_remap(
    request: Request,
    key: str = Query(..., description="관리자 키"),
    payload: dict = Body(..., example={"uid":"04AABBCCDD","token":"XYZ...","clear":False,"base_url":""})
):
    if key != ADMIN_KEY:
        raise HTTPException(403, "forbidden")

    uid = _normalize_uid(payload.get("uid",""))
    token = (payload.get("token") or "").strip()
    clear = bool(payload.get("clear", False))
    base_url = payload.get("base_url") or str(request.base_url)
    if not uid:
        raise HTTPException(400, "uid is required")

    ws = ws_responses
    col_uid = _ensure_cols(ws, ws.row_values(1), ["uid"])["uid"]
    header = [h.strip() for h in ws.row_values(1)]
    token_col_name = next((c for c in ("token","Token","토큰") if c in header), None)
    if not token_col_name:
        raise HTTPException(404, "token column missing. 먼저 /admin/generate-tokens 실행")
    col_token = header.index(token_col_name) + 1
    more = _ensure_cols(ws, header, ["url","assigned_at"])
    col_url, col_assigned_at = more["url"], more["assigned_at"]

    # 전체 읽기 1회
    matrix = ws.get_all_values()
    header = [h.strip() for h in matrix[0]]
    rows = matrix[1:]
    idx_uid = header.index("uid") if "uid" in header else None
    idx_token = header.index(token_col_name)

    def _safe(row, idx):
        return row[idx] if idx is not None and idx < len(row) else ""

    # 현재 UID 걸린 행
    row_idx_uid = None
    if idx_uid is not None:
        for i, row in enumerate(rows, start=2):
            if (_safe(row, idx_uid) or "").strip().upper() == uid:
                row_idx_uid = i
                break

    if clear:
        if not row_idx_uid:
            return {"status":"ok","message":"nothing to clear"}
        ws.batch_update([
            {"range": f"{_col_letter(col_uid)}{row_idx_uid}", "values": [[""]]},
            {"range": f"{_col_letter(col_url)}{row_idx_uid}", "values": [[""]]},
            {"range": f"{_col_letter(col_assigned_at)}{row_idx_uid}", "values": [[""]]},
        ])
        return {"status":"ok","cleared_uid": uid}

    if not token:
        raise HTTPException(400, "token is required for remap")

    # 토큰 존재 행
    row_idx_token = None
    for i, row in enumerate(rows, start=2):
        if (_safe(row, idx_token) or "").strip() == token:
            row_idx_token = i
            break
    if not row_idx_token:
        raise HTTPException(404, f"token not found: {token}")

    # 기존 UID가 다른 행에 묶여있으면 비움
    if row_idx_uid and row_idx_uid != row_idx_token:
        ws.batch_update([
            {"range": f"{_col_letter(col_uid)}{row_idx_uid}", "values": [[""]]},
            {"range": f"{_col_letter(col_url)}{row_idx_uid}", "values": [[""]]},
            {"range": f"{_col_letter(col_assigned_at)}{row_idx_uid}", "values": [[""]]},
        ])

    # 토큰 행에 UID/URL/시간 기록
    url = _construct_profile_url(base_url, token)
    now_iso = datetime.now(timezone.utc).isoformat()
    ws.batch_update([
        {"range": f"{_col_letter(col_uid)}{row_idx_token}", "values": [[uid]]},
        {"range": f"{_col_letter(col_url)}{row_idx_token}", "values": [[url]]},
        {"range": f"{_col_letter(col_assigned_at)}{row_idx_token}", "values": [[now_iso]]},
    ])
    return {"status":"ok","uid":uid,"token":token,"url":url,"remapped":True}

# ----- 스캔 기록: /u/{token}/touch -----
class TouchPayload(BaseModel):
    source: str | None = None
    campaign: str | None = None

@app.post("/u/{token}/touch")
def touch_token(token: str, body: TouchPayload | None = None):
    token = unquote(token)
    header, tokmap = _ensure_token_index(ws_responses)
    if not tokmap:
        raise HTTPException(404, "토큰 인덱스가 비어있습니다. 먼저 토큰을 생성하세요.")
    row = tokmap.get(_norm(token))
    if not row:
        raise HTTPException(404, "해당 토큰을 찾을 수 없습니다.")

    needed = ["scan_count","last_seen_at"]
    if body and body.source:   needed.append("source")
    if body and body.campaign: needed.append("campaign")
    col_idx = _ensure_cols(ws_responses, header, needed)

    # Read 1회
    col = _col_letter(col_idx["scan_count"])
    rng = f"{col}{row}:{col}{row}"
    vals = ws_responses.batch_get([rng]) or [["0"]]
    try:
        cur = int(str(vals[0][0][0]).strip() or "0")
    except Exception:
        cur = 0

    # Write 1회
    iso = datetime.now(timezone.utc).isoformat()
    updates = [
        {"range": f"{_col_letter(col_idx['scan_count'])}{row}", "values": [[str(cur+1)]]},
        {"range": f"{_col_letter(col_idx['last_seen_at'])}{row}", "values": [[iso]]},
    ]
    if body and body.source:
        updates.append({"range": f"{_col_letter(col_idx['source'])}{row}", "values": [[body.source[:64]]]})
    if body and body.campaign:
        updates.append({"range": f"{_col_letter(col_idx['campaign'])}{row}", "values": [[body.campaign[:64]]]})
    ws_responses.batch_update(updates)

    return {"status":"ok","row":row,"scan_count":cur+1,"last_seen_at":iso}

# ----- 관리자: 토큰 생성/보충 -----
@app.post("/admin/generate-tokens")
def admin_generate_tokens(
    key: str = Query(..., description="ADMIN_KEY와 동일해야 함"),
    limit: int = Query(5, ge=0, description="샘플 개수(0=전부)")
):
    if key != ADMIN_KEY:
        raise HTTPException(403, "forbidden")
    try:
        result = _ensure_token_column_and_fill(ws_responses)
        sample = result["sample"] if limit == 0 else result["sample"][:limit]
        return JSONResponse({
            "status": "ok",
            "created": result["created"],
            "token_column": result["col_name"],
            "sample": sample
        })
    except Exception as e:
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)

# ----- 디버그 -----
@app.get("/debug/columns")
def debug_columns():
    return {
        "resp_cols": _read_ws(ws_responses).columns.tolist(),
        "clu_cols":  _read_ws(ws_cluster).columns.tolist()
    }

@app.get("/users.json")
def users_json():
    return JSONResponse(_read_ws(ws_responses).to_dict(orient="records"))

@app.get("/users.csv", response_class=PlainTextResponse)
def users_csv():
    return PlainTextResponse(_read_ws(ws_responses).to_csv(index=False))

# ----- 실행 -----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("nfc_server:app", host="0.0.0.0", port=8000, reload=True)
