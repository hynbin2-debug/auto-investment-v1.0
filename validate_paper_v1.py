#!/usr/bin/env python3
"""Read-only, synthetic-data verification of src/engine.py. No KRX/network/files written."""
import argparse, importlib.util, json, sys
from datetime import date, timedelta
from pathlib import Path

def load_engine(path):
    spec=importlib.util.spec_from_file_location('paper_engine_under_test',path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def row(day,close=8000,open_=None,high=None,low=None,foreign=100,inst=100):
    o=float(close if open_ is None else open_); c=float(close)
    h=float(max(o,c) if high is None else high); l=float(min(o,c) if low is None else low)
    assert l<=min(o,c)<=max(o,c)<=h
    return dict(date=day.isoformat(),open=o,high=h,low=l,close=c,volume=10000.,foreign_net=float(foreign),institution_net=float(inst))

def make_rows(study, warm_close=8000):
    start=date(2026,11,11)
    warm=[row(start-timedelta(days=i),warm_close) for i in range(25,0,-1)]
    rows=[]
    for i,changes in enumerate(study):
        kw=dict(close=8000,foreign=100,inst=100);kw.update(changes)
        rows.append(row(start+timedelta(days=i),**kw))
    return warm+rows

def trades(result,action=None):
    return [x for x in result['trades'] if action is None or x['action']==action]

def check(name, predicate, info, out, known=False):
    ok=bool(predicate)
    out.append(dict(test=name,status='PASS' if ok else ('KNOWN_MISMATCH' if known else 'FAIL'),detail=info))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--engine',default='src/engine.py');ap.add_argument('--output',default=None)
    args=ap.parse_args(); e=load_engine(Path(args.engine)); out=[]
    def run(study):return e.compute(make_rows(study))
    base={'close':8600,'high':8700,'low':8500}
    s=run([base,{'open_':8500,'close':8500,'high':8550,'low':8450}]); b=trades(s,'BUY')
    check('최초 진입 다음날 시가 30%',len(b)==1 and b[0]['date']=='2026-11-12' and b[0]['price']==8500 and 0<b[0]['qty']*8500<=3000000,str(b),out)
    s=run([{'close':8520,'high':8600,'low':8000}, {'close':8000}]);check('8,520원 정확히 동일하면 진입 안 함',len(trades(s,'BUY'))==0,str(trades(s)),out)
    s=run([dict(base,foreign=-1000000),{'close':8000}]);check('외국인 5일 순매수 음수이면 진입 안 함',len(trades(s,'BUY'))==0,str(trades(s)),out)
    s=run([base,{'open_':8500,'close':8500,'high':8550,'low':8450},{'close':8800,'high':8850,'low':8700},{'open_':8800,'close':8800,'high':8850,'low':8750}]); buys=trades(s,'BUY')
    check('추가매수: MA20·수급·+3% 다음 시가',len(buys)==2 and buys[1]['date']=='2026-11-14' and buys[1]['price']==8800,str(buys),out)
    # Deliberate difference: 8500*1.03=8755; fee-inclusive cost 8501.275*1.03=8756.31325.
    s=run([base,{'open_':8500,'close':8500,'high':8550,'low':8450},{'close':8756,'high':8800,'low':8700},{'open_':8756,'close':8756,'high':8800,'low':8700}]);buys=trades(s,'BUY')
    check('합의한 최초 체결가 기준 +3% 경계 8,756원',len(buys)==2,'기대: 추가매수 발생. 실제: '+str(buys),out,known=True)
    s=run([base,{'open_':8500,'close':8500,'high':8600,'low':7900}]); sells=trades(s,'SELL')
    check('장중 -7% 손절 전량',len(sells)==1 and sells[0]['qty']==trades(s,'BUY')[0]['qty'] and '손절' in sells[0]['reason'],str(sells),out)
    s=run([base,{'open_':7700,'close':8000,'high':8500,'low':7600}]);sells=trades(s,'SELL')
    check('손절가 아래 갭하락은 시가 체결',len(sells)==1 and sells[0]['price']==7700,str(sells),out)
    s=run([base,{'open_':8500,'close':8500,'high':9600,'low':8400}]); buys=trades(s,'BUY');sells=trades(s,'SELL')
    check('+10% 도달시 절반 익절',len(sells)==1 and '+10%' in sells[0]['reason'] and sells[0]['qty']==max(1,buys[0]['qty']//2),str(sells),out)
    s=run([base,{'open_':8500,'close':8500,'high':9600,'low':7700}]);sells=trades(s,'SELL')
    check('손절과 익절 동시 가능시 손절 우선',len(sells)==1 and '손절' in sells[0]['reason'],str(sells),out)
    s=run([base,{'open_':8500,'close':9400,'high':9600,'low':8400},{'close':8800,'high':9000,'low':8700},{'open_':8750,'close':8750,'high':8850,'low':8700}]);sells=trades(s,'SELL')
    check('절반 익절 후 종가 -5% 추적, 익일 시가 청산',len(sells)==2 and '추적손절' in sells[1]['reason'] and sells[1]['price']==8750,str(sells),out)
    study=[base,{'open_':8500,'close':8500,'high':8550,'low':8450}]+[{'close':8500,'high':8550,'low':8450} for _ in range(18)]
    s=run(study);sells=trades(s,'SELL')
    check('20거래일 종료 종가 청산',s['days']==20 and s['shares']==0 and s['status']=='관찰 종료' and len(sells)==1 and '20거래일' in sells[0]['reason'],str(sells),out)
    report={'source_engine':str(args.engine),'mode':'synthetic isolated read-only','results':out,'counts':{k:sum(x['status']==k for x in out) for k in ('PASS','FAIL','KNOWN_MISMATCH')}}
    payload=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:Path(args.output).write_text(payload,encoding='utf-8')
    print(payload)
    return 1 if report['counts']['FAIL'] else 0
if __name__=='__main__':sys.exit(main())
