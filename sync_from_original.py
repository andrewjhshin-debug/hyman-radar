"""오리지날(watchlist-chart)의 watch.py·episodes_w.json 을 상업용으로 가져온다. 상업 종목 목록만 끼워 넣음.
오리지날 엔진을 고친 뒤 상업에도 반영할 때: python -X utf8 sync_from_original.py"""
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORIG = HERE.parent / "watchlist-chart"
BLOCK = '''# ── 상업(하이먼 레이더): 거시 지표 + 고르는 대형주 ──
MACRO = [('^KS11', '코스피'), ('^KQ11', '코스닥'), ('^IXIC', '나스닥'), ('^SOX', '필라델피아 반도체'), ('upbit:KRW-BTC', '비트코인'), ('GC=F', '금')]
MAJORS = [('005930.KS', '삼성전자'), ('000660.KS', 'SK하이닉스'), ('373220.KS', 'LG에너지솔루션'), ('207940.KS', '삼성바이오로직스'), ('005380.KS', '현대차'), ('012450.KS', '한화에어로스페이스'), ('034020.KS', '두산에너빌리티'), ('AAPL', '애플'), ('MSFT', '마이크로소프트'), ('NVDA', '엔비디아'), ('GOOGL', '알파벳'), ('AMZN', '아마존'), ('META', '메타'), ('TSLA', '테슬라'), ('AVGO', '브로드컴'), ('TSM', 'TSMC'), ('PLTR', '팔란티어'), ('SPCX', '스페이스X'), ('ANT', '앤트로픽')]
HA = MACRO + MAJORS
EXTRA = []
ALWAYS_HA = {s_ for s_, _ in HA}


'''
s = (ORIG / "watch.py").read_text(encoding="utf-8")
A = "def minsky_html() -> str:\n"
assert s.count(A) == 1
s = s.replace(A, BLOCK + A)
(HERE / "watch.py").write_text(s, encoding="utf-8")
shutil.copy(ORIG / "episodes_w.json", HERE / "episodes_w.json")
print("synced watch.py + episodes_w.json from", ORIG)
