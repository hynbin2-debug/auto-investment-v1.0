"""Send the latest paper-trading report via SMTP, without storing credentials."""
import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
state = json.loads((ROOT / "docs/state.json").read_text(encoding="utf-8"))
journal = json.loads((ROOT / "docs/journal.json").read_text(encoding="utf-8"))
if state.get("data_status") != "실측 데이터 로드" or journal["source_last_date"] != state["last_date"]:
    raise SystemExit("Report data is missing or inconsistent")
if not journal["records"]:
    raise SystemExit("No daily records")
host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
port = int(os.environ.get("SMTP_PORT", "587"))
user = os.environ["SMTP_USER"]
password = os.environ["SMTP_PASSWORD"]
recipient = os.environ["REPORT_EMAIL_TO"]
last = journal["records"][-1]
msg = EmailMessage()
msg["Subject"] = f"[모의투자] 아이마켓코리아 {last['date']} 일일 투자일지"
msg["From"] = user
msg["To"] = recipient
msg.set_content(
    f"아이마켓코리아(122900) 자동 모의투자\n"
    f"기준일: {last['date']}\n"
    f"판단: {last['decision']}\n"
    f"사유: {last['reason']}\n"
    f"종가: {last['close']:,.0f}원\n"
    f"보유: {last['shares']}주\n"
    f"현금: {last['cash']:,.0f}원\n"
    f"총자산: {last['equity']:,.0f}원\n"
    f"누적 수익률: {state['return_pct']:+.2f}%\n"
    f"최대 낙폭: {state['max_drawdown_pct']:.2f}%\n"
    f"매매 건수(당일): {len(last['trades'])}\n\n"
    "연구용 모의투자이며 실제 주문이 아닙니다.\n"
)
# Naver SMTP: STARTTLS and standard SMTP authentication.
# Do not print credentials or server response text.
stage = "connect"
try:
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        stage = "starttls"
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        stage = "login"
        smtp.login(user, password)
        stage = "send"
        smtp.send_message(msg)
except smtplib.SMTPResponseException as exc:
    print(f"SMTP failed at {stage}: {type(exc).__name__}; status={exc.smtp_code}", flush=True)
    raise SystemExit(1) from None
except (smtplib.SMTPException, OSError, TimeoutError) as exc:
    print(f"SMTP failed at {stage}: {type(exc).__name__}", flush=True)
    raise SystemExit(1) from None
print("Daily report sent")
