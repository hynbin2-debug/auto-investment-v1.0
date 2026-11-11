import csv, json, math, os
from datetime import datetime, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; DOCS=ROOT/'docs'
TICKER='122900'; START='2026-11-11'; INITIAL=10_000_000
FEE=float(os.getenv('PAPER_FEE_RATE','0.00015')); TAX=float(os.getenv('PAPER_SELL_TAX_RATE','0.002'))

def load_rows():
    path=DATA/'daily.csv'
    if not path.exists(): return []
    with path.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    out=[]
    for r in rows:
        try:
            x={k:float(r[k]) for k in ('open','high','low','close','volume','foreign_net','institution_net')}
            if not (x['low']<=x['open']<=x['high'] and x['low']<=x['close']<=x['high'] and x['volume']>=0): raise ValueError('OHLC inconsistent')
            x['date']=r['date']; out.append(x)
        except (KeyError,ValueError) as e: raise ValueError(f"Invalid data on {r.get('date','?')}: {e}")
    out.sort(key=lambda x:x['date'])
    if len(set(x['date'] for x in out))!=len(out): raise ValueError('duplicate dates')
    return out

def load_reference():
    # Verified baseline from the agreed pilot; never use as a fabricated daily observation.
    return {'date':'2026-11-10','close':8380,'high':8520,'foreign_5d':19.60,'institution_5d':8.86}

def ma20(closes):
    return sum(closes[-20:])/20 if len(closes)>=20 else None

def compute(rows):
    base=load_reference(); cash=float(INITIAL); shares=0; cost=0.; peak_close=None; half_taken=False
    entry_pending=False; add_pending=False; exit_pending=False; logs=[]; equity=[]; close_history=[]; last5=[]; first_entry=None; first_entry_price=None
    notes=[]; last_date=base['date']; benchmark_shares=0; benchmark_cash=INITIAL; benchmark_started=False
    study_rows=[r for r in rows if r['date']>=START][:20]
    warmup=[r for r in rows if r['date']<START]
    if study_rows and len(warmup)<20: raise ValueError('MA20 warm-up requires 20 verified earlier trading sessions')
    close_history=[r['close'] for r in warmup]
    last5=warmup[-4:]
    for idx,r in enumerate(study_rows):
        day=r['date']; last_date=day; o,h,l,c=(r[k] for k in ('open','high','low','close'))
        # Benchmark: fixed 5m exposure, opening price on first observation.
        if not benchmark_started:
            benchmark_shares=math.floor(5_000_000/(o*(1+FEE)))
            benchmark_cash-=benchmark_shares*o*(1+FEE)
            benchmark_started=True
        # Pending close signal executes next session at OPEN.
        if exit_pending and shares:
            cash+=shares*o*(1-FEE-TAX); logs.append({'date':day,'action':'SELL','price':o,'qty':shares,'reason':'종가 추적손절 → 익일 시가','cash':round(cash)})
            shares=0; cost=0; exit_pending=False
        if entry_pending and shares==0:
            qty=math.floor((INITIAL*.30)/(o*(1+FEE)))
            if qty>0 and qty*o*(1+FEE)<=cash:
                cash-=qty*o*(1+FEE); shares=qty; cost=o*(1+FEE); first_entry=day; first_entry_price=o; peak_close=c; half_taken=False
                logs.append({'date':day,'action':'BUY','price':o,'qty':qty,'reason':'전일 돌파+5일 외국인·기관 순매수 → 익일 시가','cash':round(cash)})
            entry_pending=False
        if add_pending and shares and not half_taken:
            budget=min(INITIAL*.20, INITIAL*.50-shares*o)
            qty=max(0,math.floor(budget/(o*(1+FEE))))
            if qty and qty*o*(1+FEE)<=cash:
                old_total=shares*cost; cash-=qty*o*(1+FEE)
                cost=(old_total+qty*o*(1+FEE))/(shares+qty); shares+=qty
                logs.append({'date':day,'action':'BUY','price':o,'qty':qty,'reason':'전일 MA20·수급·+3% 추가매수 → 익일 시가','cash':round(cash)})
            add_pending=False
        # Intraday ambiguous ordering: stop always first. A gap below stop fills at open.
        if shares:
            stop=cost*.93
            if l<=stop:
                px=o if o<stop else stop
                cash+=shares*px*(1-FEE-TAX)
                logs.append({'date':day,'action':'SELL','price':round(px,2),'qty':shares,'reason':'-7% 손절 (보수적 우선 체결)','cash':round(cash)})
                shares=0; cost=0; exit_pending=False; add_pending=False
            elif not half_taken and h>=cost*1.10:
                qty=max(1,shares//2); px=cost*1.10
                cash+=qty*px*(1-FEE-TAX); shares-=qty; half_taken=True
                logs.append({'date':day,'action':'SELL','price':round(px,2),'qty':qty,'reason':'+10% 절반 익절','cash':round(cash)})
        close_history.append(c); last5.append(r); last5=last5[-5:]
        ma=ma20(close_history)
        # No historical MA20 is available from the start of this study; only calculate after 20 observed sessions.
        flow_ok=len(last5)==5 and sum(x['foreign_net'] for x in last5)>0 and sum(x['institution_net'] for x in last5)>0
        if shares:
            peak_close=max(peak_close or c,c)
            if half_taken and c<=peak_close*.95: exit_pending=True
            # v1.0 add-on only when close +3%, above MA20 and both flows positive; executes next open.
            # Add-on is not evaluated unless 20 actual observed closes exist.
            if idx<19 and ma is not None and flow_ok and c>ma and c>=first_entry_price*1.03 and shares*cost < INITIAL*.50 and not half_taken:
                add_pending=True
        elif not first_entry:
            # Entry: today's close strictly ABOVE fixed 8,520 and rolling 5d flows each positive.
            if idx<19 and c>8520 and flow_ok: entry_pending=True
        portfolio=cash+shares*c
        benchmark=benchmark_cash+benchmark_shares*c
        equity.append({'date':day,'equity':round(portfolio),'cash':round(cash),'shares':shares,'close':c,'benchmark':round(benchmark),'ma20':round(ma,2) if ma else None,'flow5_ok':flow_ok})
    # Fixed 20-session horizon: liquidation at last close, explicitly marked as close-price assumption.
    if len(study_rows)>=20 and shares:
        r=study_rows[19]; px=r['close']; cash+=shares*px*(1-FEE-TAX)
        logs.append({'date':r['date'],'action':'SELL','price':px,'qty':shares,'reason':'20거래일 종료 종가 가상청산','cash':round(cash)})
        shares=0; equity[-1]['equity']=round(cash); equity[-1]['cash']=round(cash); equity[-1]['shares']=0
    peaks=[]; maxdd=0
    for e in equity:
        peaks.append(max(e['equity'],peaks[-1] if peaks else INITIAL))
        maxdd=min(maxdd,e['equity']/peaks[-1]-1)
    return {'version':'1.0','ticker':TICKER,'name':'아이마켓코리아','start':START,'last_date':last_date,'status':('관찰 종료' if len(study_rows)>=20 else '보유' if shares else '진입 대기' if not first_entry else '청산 후 관찰'),'initial':INITIAL,'cash':round(cash),'shares':shares,'equity':equity[-1]['equity'] if equity else INITIAL,'return_pct':round(((equity[-1]['equity'] if equity else INITIAL)/INITIAL-1)*100,3),'max_drawdown_pct':round(maxdd*100,3),'benchmark_equity':equity[-1]['benchmark'] if equity else None,'benchmark_note':'첫 관찰일 시가에 500만원 매수, 나머지 현금; 동일 비용 가정 (최종 매도 비용 미반영)','days':len(equity),'trades':logs,'curve':equity,'notes':notes,'baseline':base,'data_status':'실측 데이터 로드' if equity else '데이터 없음','assumptions':['KRX 일봉과 투자자 순매수 거래대금 사용','동일 일자 손절과 익절 모두 가능하면 손절 우선','장중 손절 갭하락은 시가 체결 가정','시가/종가 주문은 실제 체결가를 보장하지 않음','MA20은 관찰 시작 전 검증된 일봉 20개 이상을 포함하여 계산','추가매수는 MA20과 수급이 확인된 후에만 다음 거래일 시가로 가상 체결']}

def main():
    DOCS.mkdir(exist_ok=True)
    result=compute(load_rows())
    (DOCS/'state.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('state updated:',result['last_date'],result['data_status'],result['days'])
if __name__=='__main__':main()
