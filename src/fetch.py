"""Fetch verified historical OHLCV and investor net trading value for 122900.
No synthetic observations; a failed fetch raises an error and leaves previous CSV untouched.
"""
import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'data' / 'daily.csv'
FIELDS = ['date','open','high','low','close','volume','foreign_net','institution_net']
START = '20260901'  # warm-up for MA20 and 5-session investor flows


def main():
    from pykrx import stock
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    end = today.strftime('%Y%m%d')
    if today < date(2026, 11, 11):
        raise RuntimeError('모의투자 첫 관찰일(2026-11-11) 이전입니다. 데이터 수집을 시작하지 않습니다.')
    prices = stock.get_market_ohlcv_by_date(START, end, '122900')
    flows = stock.get_market_trading_value_by_date(START, end, '122900')
    if prices is None or prices.empty or flows is None or flows.empty:
        raise RuntimeError('KRX 가격 또는 투자자 수급 데이터가 비어 있습니다. CSV를 변경하지 않습니다.')
    rows = []
    for dt, p in prices.iterrows():
        if dt not in flows.index:
            raise RuntimeError(f'KRX 수급 데이터 누락: {dt}')
        f = flows.loc[dt]
        try:
            row = [dt.strftime('%Y-%m-%d'), int(p['시가']), int(p['고가']), int(p['저가']), int(p['종가']), int(p['거래량']), int(f['외국인합계']), int(f['기관합계'])]
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f'KRX 데이터 형식 오류 {dt}: {exc}') from exc
        if row[1] <= 0 or row[2] <= 0 or row[3] <= 0 or row[4] <= 0 or row[3] > min(row[1], row[4]) or row[2] < max(row[1], row[4]):
            raise RuntimeError(f'OHLC 오류: {row[0]}')
        rows.append(row)
    if not rows or rows[-1][0] < '2026-11-11':
        raise RuntimeError('관찰 시작일 이후 실제 데이터가 없습니다. CSV를 변경하지 않습니다.')
    if len([r for r in rows if r[0] < '2026-11-11']) < 20:
        raise RuntimeError('MA20 계산용 과거 거래일이 20일 미만입니다.')
    PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PATH.with_suffix('.tmp')
    with tmp.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(FIELDS)
        writer.writerows(rows)
    tmp.replace(PATH)
    print(f'KRX verified rows: {len(rows)}, first={rows[0][0]}, last={rows[-1][0]}')

if __name__ == '__main__':
    main()
