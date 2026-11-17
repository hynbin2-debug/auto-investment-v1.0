"""Build an auditable daily decision journal without changing the trading engine."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "docs" / "state.json"
OUTPUT = ROOT / "docs" / "journal.json"

def build(state):
    trades_by_day = {}
    for trade in state.get("trades", []):
        trades_by_day.setdefault(trade["date"], []).append(trade)
    records = []
    for row in state.get("curve", []):
        date = row["date"]
        trades = trades_by_day.get(date, [])
        if trades:
            decision = " / ".join("매수" if t["action"] == "BUY" else "매도" for t in trades)
            reason = " / ".join(t["reason"] for t in trades)
        elif row["shares"]:
            decision = "보유"
            reason = "당일 가상 매매 없음; 기존 보유 유지"
        else:
            decision = "관망"
            reason = ("진입 기준 종가 8,520원 초과 미충족" if row["close"] <= 8520
                      else "진입 조건 또는 주문 대기 상태; 매매 없음")
            if row.get("flow5_ok") is False:
                reason += "; 외국인·기관 5일 동반 순매수 미충족"
        records.append({
            "date": date, "decision": decision, "reason": reason,
            "close": row["close"], "ma20": row.get("ma20"),
            "flow5_ok": row.get("flow5_ok"), "shares": row["shares"],
            "cash": row["cash"], "equity": row["equity"],
            "trades": trades,
        })
    return {"version": "1.0", "source_last_date": state.get("last_date"),
            "data_status": state.get("data_status"), "records": records}

if __name__ == "__main__":
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("data_status") != "실측 데이터 로드":
        raise SystemExit("Verified market data unavailable")
    journal = build(state)
    OUTPUT.write_text(json.dumps(journal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Journal records:", len(journal["records"]))
