from fastapi import FastAPI, HTTPException
import gspread
import pandas as pd

app = FastAPI(debug=True)

# 1) 경로 채우기
SERVICE_ACCOUNT_FILE = r""
try:
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
except Exception as e:
    print("❌ service_account 에러:", e)
    raise

# 2) 시트 열기
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1kkt336f1G-XqfDuwCUOnqpKlxTcnwLQy-XS4SQv6lM0/edit"
sh = gc.open_by_url(spreadsheet_url)
print(">> available worksheets:", [ws.title for ws in sh.worksheets()])

# 3) 워크시트 접근 (이름 확인 후 정확히 매칭)
ws_responses = sh.worksheet("설문지 응답 시트")
ws_cluster   = sh.worksheet("Clustered Result with Distance")

@app.get("/display/{name}")
def get_display_data(name: str):
    try:
        df_resp = pd.DataFrame(ws_responses.get_all_records())
        resp = df_resp[df_resp["이름"] == name]
        if resp.empty:
            raise HTTPException(status_code=404, detail="설문 응답에 사용자 없음")
        resp = resp.iloc[0]

        df_clu = pd.DataFrame(ws_cluster.get_all_records())
        clu = df_clu[df_clu["이름"] == name]
        if clu.empty:
            raise HTTPException(status_code=404, detail="클러스터 시트에 사용자 없음")
        clu = clu.iloc[0]

        return {
            "이름": resp["이름"],
            "학교": resp.get("학교", ""),
            "학년": resp.get("학년", ""),
            "전공": resp.get("전공", ""),
            "이메일": resp.get("이메일 주소", resp.get("이메일", "")),
            "Top_Industries": clu.get("Top Industries", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        print("❌ get_display_data 에러:", repr(e))
        raise HTTPException(status_code=500, detail="Internal Server Error")

