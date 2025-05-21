from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import gspread
import pandas as pd

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# ✅ Google API 인증 (서비스 계정 키 사용)
SERVICE_ACCOUNT_FILE = r""
gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)

# ✅ Google Sheets 연결
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1kkt336f1G-XqfDuwCUOnqpKlxTcnwLQy-XS4SQv6lM0/edit"
sh = gc.open_by_url(spreadsheet_url)

# 시트 선택
ws_responses = sh.worksheet("설문지 응답 시트")
ws_cluster = sh.worksheet("Clustered Result with Distance")

# ✅ 사용자 상세정보 페이지 라우팅
@app.get("/user/{name}", response_class=HTMLResponse)
def render_user_profile(request: Request, name: str):
    # 설문 응답 로드
    df_resp = pd.DataFrame(ws_responses.get_all_records())
    resp_match = df_resp[df_resp["이름"] == name]
    if resp_match.empty:
        raise HTTPException(status_code=404, detail="설문 응답에 사용자 없음")
    resp = resp_match.iloc[0]

    # 클러스터 결과 로드
    df_clu = pd.DataFrame(ws_cluster.get_all_records())
    clu_match = df_clu[df_clu["이름"] == name]
    if clu_match.empty:
        raise HTTPException(status_code=404, detail="클러스터 결과에 사용자 없음")
    clu = clu_match.iloc[0]

    # 템플릿 렌더링
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": {
            "name": resp["이름"],
            "school": resp.get("학교", ""),
            "year": resp.get("학년", ""),
            "major": resp.get("전공", ""),
            "email": resp.get("이메일 주소", resp.get("이메일", "")),
            "top_industries": clu.get("Top Industries", clu.get("top_industries", "")),
        }
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
