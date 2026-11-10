# 아이마켓코리아 자동 모의투자 v1.0

GitHub Actions에서 KRX 기반 일별 시세·수급을 수집하고, 정해진 규칙으로 매매일지를 **처음부터 재계산**해 GitHub Pages에서 확인하는 모바일 웹사이트입니다. 실거래는 하지 않습니다.

## 모바일 설치 (새 저장소)
1. ZIP 압축을 풀어 GitHub 새 **공개** 저장소에 폴더 구조 그대로 업로드합니다 (`.github` 숨김 폴더 포함). 기존 본 검색 저장소와 분리 권장.
2. Settings → Actions → General → Workflow permissions → **Read and write permissions** 허용.
3. Settings → Pages → Build and deployment → **Deploy from a branch** → `main` / `/docs` → Save.
4. Actions → **아이마켓코리아 자동 모의투자** → Run workflow. 성공 후 `https://계정명.github.io/저장소명/` 에 접속합니다.

## 데이터 수집 및 주의사항
- `src/fetch.py`는 **pykrx KRX 데이터 인터페이스**를 사용합니다. KRX 측 접속 정책/인증 변경 시 동작이 보장되지 않습니다. **기존 로그인 기반 KRX 수집기의 로그인 기능을 제거하지 마세요.** 기존 수집기를 사용한다면 `data/daily.csv` 형식으로 출력하도록 연결하고 workflow의 Fetch 단계만 교체하세요.
- 컬럼: `date,open,high,low,close,volume,foreign_net,institution_net` (수급은 **원**, 5일 합산은 양수 여부만 사용).
- KRX 응답 실패 시 작업은 실패하며 **마지막 성공 데이터가 유지**됩니다. 임의 데이터 생성 금지.
- 2026-11-11부터 20거래일만 평가. 2026-11-10 기준 종가 8,380원과 고가 8,520원은 신호 기준으로만 사용합니다. 최초 5거래일은 5일 수급 이력이 없어 진입 신호를 내지 않습니다. MA20은 관찰일 이후 20개 종가가 있어야 계산됩니다. 이전 20거래일 데이터를 연동하면 초기 MA20을 개선할 수 있습니다.
- 자동 실행: 평일 19:30 KST. GitHub Actions schedule은 지연될 수 있고 휴장일엔 기존 상태를 유지합니다.
- **장중 손절·익절 순서 확인 불가:** 같은 날 둘 다 가능하면 손절을 우선합니다. 갭하락 시 시가 체결로 가정합니다. 종가 신호는 다음 거래일 시가 체결, 20거래일 종료는 당일 종가 체결 가정입니다.
- 모의 수수료 매수/매도 0.015%, 매도 세금 0.2%는 연구용 기본값이며 실제 시장 세율 및 증권사 비용과 다를 수 있습니다. 환경변수 `PAPER_FEE_RATE`, `PAPER_SELL_TAX_RATE`로 변경 가능합니다.
- 비교전략은 관찰 첫날 시가에 500만 원만 매수, 나머지 현금 보유. 마지막 매도 비용은 반영하지 않아 비교 한계가 있습니다.
- 원래 합의한 +3% 추가매수 조건과 +10% 절반 익절, 최고 종가 -5% 추적매도, -7% 손절을 유지합니다. 추가매수는 20일선 확인이 가능할 때만 적용합니다.
- 사이트는 공개 GitHub Pages이므로 실제 계좌번호·개인 거래내역·비밀번호를 저장하지 마세요.

## 로컬 실행
`pip install -r requirements.txt && python src/fetch.py && python src/engine.py`

`docs/state.json`이 자동 생성됩니다. 초기 상태는 매매 없음, 1,000만 원입니다.
