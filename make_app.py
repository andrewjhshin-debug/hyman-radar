"""판매용 시안 app.html 만들기.
같은 폴더 watch.py(베타 복사본)로 먼저 index.html 을 빌드한 뒤: python -X utf8 make_app.py
하이먼 칸 그림·숫자·근거는 index.html 에서 가져오고, 차트 탭 선은 주봉 2년을 새로 받는다.
출시 기념으로 구독 기능(종목 추가·근거 보기)을 모두 무료로 열어 둠. 자동 갱신은 .github/workflows/update.yml."""
import html, json, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
KST = timezone(timedelta(hours=9))
sys.path.insert(0, ".")
import watch as w

DROP = {"S&P500", "WTI 원유", "달러/원"}  # 사용자 요청으로 뺌(11-20)
SRC = open("index.html", encoding="utf-8").read()
STAGES = [t for _, t in w.STAGES]
GROUP = {"상승": ("#ffb300", STAGES[:6]), "고점": ("#ff4d5e", STAGES[6:7]), "하락": ("#ff8a3d", STAGES[7:11]),
         "바닥": ("#3ddc84", STAGES[11:12]), "회복": ("#4cc9f0", STAGES[12:])}
col = lambda st: next(c for c, ss in GROUP.values() if st in ss)
grp = lambda st: next(g for g, (c, ss) in GROUP.items() if st in ss)
MACRO = [n for _, n in w.MACRO if n not in DROP]
num = lambda t: float(re.sub(r"[^\d.]", "", t) or 0) * (1e8 if "억" in t else 1e4 if "만" in t else 1)

def fit_np(svg):
    """노란 점 가격·전저 글자가 오른쪽 끝을 넘으면 점 왼쪽으로(오리지날의 placeNps 와 같은 일을 미리)."""
    m = re.search(r'<circle cx="([\d.]+)"[^>]*class="mk-d"/><text class="mk-np" x="([\d.]+)"', svg)
    if not m or float(m.group(1)) < 120:
        return svg
    x = f"{float(m.group(1)) - 8:.1f}"
    svg = re.sub(r'<text class="mk-np" x="[\d.]+"', f'<text class="mk-np" text-anchor="end" x="{x}"', svg, count=1)
    return re.sub(r'(<tspan class="np-lo" x=")[\d.]+', lambda mm: mm.group(1) + x, svg, count=1)


items = []
for m in re.finditer(r'<div class="mk" data-k="([^"]+)" data-s="([^"]+)"[^>]*?data-st="(\d+)"([^>]*)><b><span class="mk-n"([^>]*)>.*?(<svg viewBox.*?</svg>)', SRC, re.S):
    name, sym, st, attrs, nattrs, svg = html.unescape(m.group(1)), m.group(2), int(m.group(3)), m.group(4), m.group(5), m.group(6)
    if name in DROP:
        continue
    a = dict(re.findall(r'data-(\w+)="([^"]*)"', attrs)); na = dict(re.findall(r'data-(\w+)="([^"]*)"', nattrs))
    t = lambda cls: re.sub("<.*?>", "", (re.search(r'<text class="%s"[^>]*>(.*?)</text>' % cls, svg, re.S) or [None, ""])[1])
    items.append(dict(k=name, sym=sym, macro=name in MACRO, stage=STAGES[st], st=st, ap=float(a["ap"]) if "ap" in a else None,
                      gp=float(a.get("gp", 0)), az="az" in a, ad=a.get("ad"), np=re.sub("<.*?>", "", (re.search(r'<tspan class="np-v">(.*?)</tspan>', svg) or [None, ""])[1]) or t("mk-np"),
                      zz=t("mk-zp mk-zz"), pk=t("mk-zp mk-pk"), rng="\n".join(html.unescape(na.get("chg", "")).split("\n")[:2]) if "좌절 범위" in html.unescape(na.get("chg", "")) else "",
                      fit=int(na.get("r", 0)), why=html.unescape(na.get("why", "")),
                      svg=fit_np(re.sub(r'<g class="mk-t hz-lb">.*?</g>', "", svg, flags=re.S))))
print(len(items), "개")


def weekly(sym):
    try:
        if sym.startswith("upbit:"):
            q = w.upbit_weeks(sym)[0]
        else:
            q = w.get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(sym)}?interval=1wk&range=2y")["chart"]["result"][0]
        return [v for v in q["indicators"]["quote"][0]["close"] if v][-104:]
    except Exception as e:
        print("주봉 실패", sym, e); return []


def years(sym):  # 년봉: 월봉 전체를 해마다 묶음
    if sym.startswith("upbit:"):
        rows = w.get_json(f"https://api.upbit.com/v1/candles/months?market={sym[6:]}&count=200")[::-1]
        m = [(r["candle_date_time_kst"][:4], r["opening_price"], r["high_price"], r["low_price"], r["trade_price"]) for r in rows]
    else:
        q = w.get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(sym)}?interval=1mo&range=max")["chart"]["result"][0]
        o = q["indicators"]["quote"][0]
        m = [(datetime.fromtimestamp(t).strftime("%Y"), a, b, c, d) for t, a, b, c, d in zip(q["timestamp"], o["open"], o["high"], o["low"], o["close"]) if None not in (a, b, c, d)]
    out = {}
    for y, a, b, c, d in m:
        if y not in out:
            out[y] = [a, b, c, d]
        else:
            out[y] = [out[y][0], max(out[y][1], b), min(out[y][2], c), d]
    return {"d": list(out), "o": [v[0] for v in out.values()], "h": [v[1] for v in out.values()], "l": [v[2] for v in out.values()], "c": [v[3] for v in out.values()]}


def ohlc(sym):  # 차트 탭 봉: 240·일·주·월(오리지날과 같은 받기) + 년
    r6 = lambda a: [float(f"{v:.6g}") for v in a]
    out = {}
    for v in ("240", "일", "주", "월"):
        try:
            d = w.fetch(sym, v)
            out[v] = {"d": d["dates"], "o": r6(d["opens"]), "h": r6(d["highs"]), "l": r6(d["lows"]), "c": r6(d["closes"])}
        except Exception as e:
            print("봉 실패", sym, v, e)
    try:
        y = years(sym); out["년"] = {k: (r6(x) if k != "d" else x) for k, x in y.items()}
    except Exception as e:
        print("년봉 실패", sym, e)
    return out


with ThreadPoolExecutor(8) as ex:
    for it, oh in zip(items, ex.map(ohlc, [i["sym"] for i in items])):
        it["oh"] = oh
        dc = oh.get("일", {}).get("c", [])
        it["chg"] = dc[-1] / dc[-2] - 1 if len(dc) > 1 else 0
with ThreadPoolExecutor(8) as ex:
    for it, cl in zip(items, ex.map(weekly, [i["sym"] for i in items])):
        if len(cl) > 3:
            prev = cl[-2] if cl[-2] != cl[-1] else cl[-3]
            it.update(cl=[round(v, 6) for v in cl], w1=cl[-1] / prev - 1, y1=cl[-1] / cl[max(0, len(cl) - 53)] - 1)
        else:
            it.update(cl=[], w1=0, y1=0)
for it in items:
    it["pkv"], it["npv"] = num(it["pk"]), num(it["np"])
    it["dd"] = (datetime(int(it["ad"][:4]), int(it["ad"][5:7]), int(it["ad"][8:10] or 15), tzinfo=KST) - datetime.now(KST)).days if it["ad"] else 0
    it["col"], it["grp"] = col(it["stage"]), grp(it["stage"])

W_, H_, P_ = 340, 170, 14
X = lambda x: P_ + x * (W_ - 2 * P_)
Y = lambda y: H_ - 22 - y * (H_ - 50)
MODEL = dict(curve="M" + " L".join(f"{X(i / 300):.1f},{Y(w.mk(i / 300)):.1f}" for i in range(301)),
             trend=[X(0), Y(.05), X(1), Y(.22)],
             pos=[[round(X((b0 + min(b1, 1)) / 2), 1), round(Y(w.mk((b0 + min(b1, 1)) / 2)), 1)]
                  for b0, b1 in zip([0] + [x for x, _ in w.STAGES[:-1]], [x for x, _ in w.STAGES[:-1]] + [1])],
             labels=[[X(.735), Y(1) - 8, "새 논리"], [X(.92), Y(0) + 16, "좌절"], [X(.45), Y(.2) + 18, "1차 현금화"]])
DATA = dict(items=items, stages=STAGES, groups={g: c for g, (c, _) in GROUP.items()}, model=MODEL,
            defaults=dict(chart=["코스피"], bar=["코스피"], ha=["코스피"]),
            built=datetime.now(KST).strftime("%Y-%m-%d %H:%M"))

page = open("app_template.html", encoding="utf-8").read()
page = page.replace("__DATA__", json.dumps(DATA, ensure_ascii=False).replace("</", "<\\/"))
open("app.html", "w", encoding="utf-8").write(page)
print("app.html", len(page))
