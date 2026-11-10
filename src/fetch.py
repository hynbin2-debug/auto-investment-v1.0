"""KRX-derived daily price and investor-flow adapter via pykrx.
For production with an authenticated KRX collector, replace this adapter with your
existing KRX-login CSV export, keeping the data/daily.csv schema unchanged.
No credentials are stored in this repository.
"""
import csv, os, sys, time
from datetime import date, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; PATH=ROOT/'data/daily.csv'
FIELDS=['date','open','high','low','close','volume','foreign_net','institution_net']

def main():
    from pykrx import stock
    start='20261111'; end=date.today().strftime('%Y%m%d')
    if date.today()<date(2026,11,11): return
    # KRX investor amounts are KRW; use native units, not 100m KRW.
    prices=stock.get_market_ohlcv_by_date(start,end,'122900')
    flows=stock.get_market_trading_value_by_date(start,end,'122900')
    if prices is None or prices.empty or flows is None or flows.empty:
        raise RuntimeError('KRX data unavailable. No synthetic rows will be produced.')
    rows=[]
    for dt,p in prices.iterrows():
        if dt not in flows.index: continue
        f=flows.loc[dt]
        try:
            foreign=float(f['외국인합계']); institution=float(f['기관합계'])
            row=[dt.strftime('%Y-%m-%d'),int(p['시가']),int(p['고가']),int(p['저가']),int(p['종가']),int(p['거래량']),int(foreign),int(institution)]
            if row[2]<=0 or row[3]<=0: continue
            rows.append(row)
        except (KeyError,TypeError,ValueError) as exc:
            raise RuntimeError(f'Unexpected KRX schema on {dt}: {exc}') from exc
    if not rows: raise RuntimeError('No joined price/flow dates')
    PATH.parent.mkdir(exist_ok=True)
    with PATH.open('w',newline='',encoding='utf-8') as fh:
        w=csv.writer(fh); w.writerow(FIELDS); w.writerows(rows)
    print('KRX rows:',len(rows),'last:',rows[-1][0])
if __name__=='__main__': main()
