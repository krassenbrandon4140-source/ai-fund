"""AI 펀드 1000 — 실시간 모의투자 엔진.

실시간 시세(야후 파이낸스 1분봉)를 받아 '나의 투자 원칙 300'을 옮긴 규칙으로
즉시 모의 체결한다. 실제 돈은 움직이지 않는다.
"""
import json, math, os, random, threading, time, logging, copy
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

import universe as U
from universe import ASSETS, BY_Y, BY_T, TRADABLE, INDICES, market_of

KST = ZoneInfo("Asia/Seoul")
NY = ZoneInfo("America/New_York")
log = logging.getLogger("fund")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
STATE_PATH = os.path.join(DATA, "portfolio.json")
FUND_PATH = os.path.join(DATA, "fundamentals_cache.json")
SEL_PATH = os.path.join(DATA, "selection.json")


def now_kst():
    return datetime.now(KST)


def load_config():
    with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
        return json.load(f)


# ───────────────────────── 장 운영 시간 ─────────────────────────
def market_open(mkt, t=None):
    t = t or datetime.now(KST)
    if mkt == "CRYPTO":
        return True
    if mkt == "KR":
        lt = t.astimezone(KST)
        return lt.weekday() < 5 and dtime(9, 0) <= lt.time() <= dtime(15, 30)
    if mkt == "US":
        lt = t.astimezone(NY)
        return lt.weekday() < 5 and dtime(9, 30) <= lt.time() <= dtime(16, 0)
    return False


# ───────────────────────── 시세 공급자 ─────────────────────────
class YahooFeed:
    """야후 파이낸스 시세. 미국 주식은 거의 실시간, 한국 주식은 거래소 사정에 따라 지연될 수 있다."""
    name = "야후 파이낸스 실시간 시세"
    demo = False

    def __init__(self):
        import yfinance as yf
        self.yf = yf

    def live(self, symbols):
        """심볼별 {px, ts(UTC epoch), prev(전일 종가)}."""
        out = {}
        if not symbols:
            return out
        df = self.yf.download(symbols, period="2d", interval="1m", progress=False,
                              group_by="ticker", auto_adjust=False, threads=True, prepost=False)
        for s in symbols:
            try:
                sub = df[s] if len(symbols) > 1 else df
                c = sub["Close"].dropna()
                if c.empty:
                    continue
                last_ts = c.index[-1]
                day = last_ts.date()
                prev_part = c[[i.date() < day for i in c.index]]
                out[s] = dict(px=float(c.iloc[-1]), ts=last_ts.timestamp(),
                              prev=float(prev_part.iloc[-1]) if len(prev_part) else None)
            except Exception:
                continue
        # 전일 종가가 비면 일봉으로 보충
        miss = [s for s in symbols if s in out and out[s]["prev"] is None]
        if miss:
            d = self.yf.download(miss, period="5d", interval="1d", progress=False, group_by="ticker", auto_adjust=False)
            for s in miss:
                try:
                    c = (d[s] if len(miss) > 1 else d)["Close"].dropna()
                    if len(c) >= 2:
                        out[s]["prev"] = float(c.iloc[-2])
                except Exception:
                    pass
        return out

    def daily(self, symbols):
        """1년 일봉 종가 → 기술 지표 계산용."""
        res = {}
        df = self.yf.download(symbols, period="1y", interval="1d", progress=False, group_by="ticker",
                              auto_adjust=False, threads=True)
        for s in symbols:
            try:
                c = (df[s] if len(symbols) > 1 else df)["Close"].dropna()
                if len(c) > 20:
                    res[s] = [float(x) for x in c.tolist()]
            except Exception:
                pass
        return res

    def fundamentals(self, symbol):
        info = self.yf.Ticker(symbol).info or {}
        keys = ["revenueGrowth", "earningsGrowth", "operatingMargins", "grossMargins", "freeCashflow",
                "marketCap", "forwardPE", "trailingPE", "pegRatio", "priceToSalesTrailing12Months",
                "debtToEquity", "targetHighPrice", "targetMeanPrice", "sector", "industry"]
        return {k: info.get(k) for k in keys}


class DemoFeed:
    """장이 닫혀 있거나 인터넷이 막혔을 때 화면·규칙을 시험해 보는 가짜 시세. 화면에 '데모'로 표시된다."""
    name = "데모 시세(가짜 데이터)"
    demo = True

    def __init__(self, seed_prices):
        self.p = dict(seed_prices)
        self.prev = dict(seed_prices)
        self.rng = random.Random(7)

    def _px(self, s):
        if s not in self.p:
            base = {"KR": 50000.0, "US": 100.0}.get(market_of(s)[0], 100.0)
            self.p[s] = self.prev[s] = base * (0.5 + self.rng.random())
        self.p[s] *= math.exp(self.rng.gauss(0.0002, 0.006))
        return self.p[s]

    def live(self, symbols):
        t = time.time()
        return {s: dict(px=self._px(s), ts=t, prev=self.prev.get(s)) for s in symbols}

    def daily(self, symbols):
        out = {}
        for s in symbols:
            p = self.p.get(s) or self._px(s)
            series, x = [], p * 1.3
            for _ in range(250):
                x *= math.exp(self.rng.gauss(-0.001, 0.02))
                series.append(x)
            series[-1] = p
            out[s] = series
        return out

    def fundamentals(self, symbol):
        r = random.Random(hash(symbol) % 1000)
        return dict(revenueGrowth=r.uniform(-0.05, 0.45), operatingMargins=r.uniform(-0.1, 0.4),
                    freeCashflow=r.uniform(-1e9, 2e10), marketCap=r.uniform(5e8, 3e12),
                    forwardPE=r.uniform(8, 70), debtToEquity=r.uniform(5, 200), targetHighPrice=None)


DEMO_SEED = {"^GSPC": 6910.39, "^IXIC": 22617.73, "^NDX": 25028.98, "^KS11": 4708.54, "^VIX": 33.0,
             "KRW=X": 1345.9, "BTC-USD": 63442.8}


# ───────────────────────── 지표·점수 ─────────────────────────
def tech_indicators(closes):
    c = closes
    hi52 = max(c[-252:])
    ma50 = sum(c[-50:]) / min(50, len(c))
    ma200 = sum(c[-200:]) / min(200, len(c))
    gains, losses = [], []
    for a, b in zip(c[-15:-1], c[-14:]):
        d = b - a
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    ag, al = sum(gains) / 14, sum(losses) / 14
    rsi = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return dict(hi52=hi52, ma50=ma50, ma200=ma200, rsi=rsi)


def clamp(x, a=0, b=100):
    return max(a, min(b, x))


def score_asset(a, f, ind, px):
    """원칙 기반 0~100점. 값이 없는 항목은 50점(중립)으로 둔다."""
    parts, notes = {}, []
    g = f.get("revenueGrowth")
    if g is not None:   # 원칙 101·102·131·151: 매출 성장
        parts["성장"] = clamp(20 if g < 0 else 40 + g * 100 * 1.4)
        notes.append(f"매출성장 {g*100:.0f}%")
    m = f.get("operatingMargins")
    if m is not None:   # 원칙 103·104·128: 영업이익률(고성장이면 적자 일부 용인)
        base = 25 if m < 0 else 45 + m * 100 * 1.5
        if m < 0 and (g or 0) > 0.3:
            base = 45
        parts["수익성"] = clamp(base)
        notes.append(f"영업이익률 {m*100:.0f}%")
    fcf, cap = f.get("freeCashflow"), f.get("marketCap")
    if fcf is not None:  # 원칙 106·108·162: 잉여현금흐름
        y = (fcf / cap) if cap else 0
        parts["현금흐름"] = clamp(70 + min(20, y * 400)) if fcf > 0 else 30
    de = f.get("debtToEquity")
    if de is not None:   # 원칙 109·111·127: 재무 건전성
        parts["재무"] = 80 if de < 50 else 60 if de < 150 else 35
    pe = f.get("forwardPE")
    if pe is not None:   # 원칙 157·158·163·167: 밸류에이션(PEG)
        if pe <= 0:
            parts["가치"] = 35
        else:
            peg = pe / max(1.0, (g or 0.1) * 100)
            parts["가치"] = 85 if peg < 1 else 70 if peg < 2 else 50 if peg < 3 else 30
            notes.append(f"선행PER {pe:.0f}")
    elif f.get("priceToSalesTrailing12Months"):
        ps = f["priceToSalesTrailing12Months"]
        parts["가치"] = 75 if ps < 5 else 55 if ps < 12 else 35
    w = {"성장": .25, "수익성": .2, "현금흐름": .2, "재무": .1, "가치": .25}
    s = sum(w[k] * parts.get(k, 50) for k in w)
    adj = 8 if a["tech"] else -10   # 원칙 5·22·32~37: 선호 산업 우대, 38: 비기술주는 분산용
    if ind and px:
        if px > ind["ma200"]:
            adj += 4                 # 구조적 상승 추세 유지
        elif px < ind["ma200"] * 0.75:
            adj -= 6                 # 원칙 253: 장기 추세 붕괴 경계
        dd = 1 - px / ind["hi52"] if ind["hi52"] else 0
        if 0.15 <= dd <= 0.45 and s >= 62:
            adj += 5                 # 원칙 232: 조정은 우량 기업을 살 기회(단, 품질 확인 후)
    return round(clamp(s + adj), 1), parts, notes


# ───────────────────────── 엔진 ─────────────────────────
class Engine:
    def __init__(self, demo=False):
        self.cfg = load_config()
        self.lock = threading.Lock()
        # 데모 기록은 실제 기록과 섞이지 않게 별도 파일에 저장한다
        self.path = os.path.join(DATA, "portfolio_demo.json") if demo else STATE_PATH
        src = self.path if os.path.exists(self.path) else STATE_PATH
        self.state = json.load(open(src, encoding="utf-8"))
        self._migrate()
        seed = {BY_T[p["t"]]["y"]: p["px"] for p in self.state["positions"] if p["t"] in BY_T}
        if demo:
            self.feed = DemoFeed({**DEMO_SEED, **seed})
        else:
            try:
                self.feed = YahooFeed()
            except ImportError:
                log.warning("yfinance가 없어 데모 시세로 시작합니다. pip install yfinance 후 다시 실행하세요.")
                self.feed = DemoFeed({**DEMO_SEED, **seed})
        self.fund = self._load_fund_cache()
        self._load_selection()
        self.daily, self.ind = {}, {}
        self.last_daily = 0
        self.quotes = {}
        self.fx = None
        self.diag = {}
        self.scores = {}
        self.stop = False

    # 기존 대시보드 데이터와 호환
    def _migrate(self):
        S = self.state
        S.setdefault("intraday", [])
        if "cash" not in S:
            S["cash"] = float(S["history"][-1]["cash"])
        S.setdefault("live", {})
        S["meta"]["mode"] = "실시간"
        S["meta"]["next_run"] = ("장중 약 10분마다 자동 점검 (GitHub 서버)" if os.environ.get("GITHUB_ACTIONS")
                                 else f"장중 {self.cfg['tick_seconds']}초마다 실시간 점검")
        for p in S["positions"]:
            if p["t"] == "BTC":
                p["stop_pct"] = -30
            else:
                p.setdefault("stop_pct", -25)

    # ── 관찰 대상 선택 ──
    def _load_selection(self):
        try:
            d = json.load(open(SEL_PATH, encoding="utf-8"))
        except Exception:
            d = {}
        for c in d.get("custom", []):
            U.add_custom(c["y"], c.get("name"), c.get("tech", True))
        self.custom = d.get("custom", [])
        self.sel = set(d["selected"]) if "selected" in d else {a["t"] for a in TRADABLE if not a["y"].startswith("^")}
        if not os.path.exists(SEL_PATH):
            self._save_selection()

    def _save_selection(self):
        json.dump(dict(selected=sorted(self.sel), custom=self.custom), open(SEL_PATH, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    def set_selected(self, tickers, on):
        with self.lock:
            for t in tickers:
                a = BY_T.get(t)
                if not a or a not in TRADABLE or a["y"].startswith("^"):
                    continue
                (self.sel.add if on else self.sel.discard)(t)
            self._save_selection()
            if on:
                self.last_daily = 0          # 새로 켠 종목의 일봉 지표를 다음 점검 때 받는다
            self.rebuild_watch(); self._save()
        return len(self.sel)

    def add_custom(self, y, name, tech):
        import re
        y = y.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,14}", y):
            raise ValueError("티커 형식이 올바르지 않습니다. 예: AMD, 005380.KS, 035420.KQ")
        if market_of(y)[0] not in ("US", "KR"):
            raise ValueError("매매는 미국(AMD)·한국(005380.KS / 코스닥은 .KQ) 종목만 추가할 수 있습니다.")
        with self.lock:
            a = U.add_custom(y, name, tech)
            if not any(c["y"] == y for c in self.custom):
                self.custom.append(dict(y=y, name=a["name"], tech=bool(tech)))
            self.sel.add(a["t"]); self.last_daily = 0
            self._save_selection(); self.rebuild_watch(); self._save()
        return a

    def remove_custom(self, t):
        with self.lock:
            if any(p["t"] == t for p in self.state["positions"]):
                raise ValueError("보유 중인 종목은 삭제할 수 없습니다. 관찰 대상에서 끄면 새로 사지 않습니다.")
            a = BY_T.get(t)
            if not a or not a.get("custom"):
                raise ValueError("직접 추가한 종목만 삭제할 수 있습니다.")
            self.custom = [c for c in self.custom if c["y"] != a["y"]]
            U.remove_custom(t); self.sel.discard(t)
            self._save_selection(); self.rebuild_watch(); self._save()

    def reload_selection(self):
        """다른 곳(GitHub 편집 등)에서 바뀐 관찰 대상 파일을 다시 읽는다."""
        with self.lock:
            before = set(self.sel)
            self._load_selection()
            if self.sel - before:
                self.last_daily = 0

    def active(self):
        """시세·점수를 계산할 종목: 선택한 종목 + 보유 종목."""
        held = {p["t"] for p in self.state["positions"]}
        return [a for a in TRADABLE if not a["y"].startswith("^") and (a["t"] in self.sel or a["t"] in held)]

    def rebuild_watch(self):
        S = self.state
        old = {it["t"]: it for g in S.get("watchlist", []) for it in g["items"]}
        held = {p["t"] for p in S["positions"]}
        rank = [BY_Y[y]["t"] for y, s in sorted(self.scores.items(), key=lambda x: -x[1]["score"])
                if BY_Y.get(y) and BY_Y[y]["t"] in self.sel][:15]
        groups, order = {}, []
        for a in ASSETS:
            if a["group"] not in groups:
                groups[a["group"]] = []; order.append(a["group"])
            y, t = a["y"], a["t"]
            tradable = a in TRADABLE and not y.startswith("^")
            sc, q = self.scores.get(y), self.quotes.get(y)
            if t in held:
                st = "보유"
            elif t in self.cfg["avoid"]:
                st = "회피"
            elif y.startswith("^"):
                st = "지표"
            elif not tradable:
                st = "관찰만"
            elif t not in self.sel:
                st = "제외"
            elif t in rank:
                st = "관찰"
            else:
                st = "중립"
            it = dict(t=t, name=a["name"], status=st, sel=t in self.sel, tradable=tradable,
                      tech=a["tech"], custom=bool(a.get("custom")))
            if st == "회피":
                it["note"] = self.cfg["avoid"][t]
            elif sc:
                px = f" · 현재가 {q['px']:,.2f}" if q else ""
                it["note"] = f"원칙 점수 {sc['score']:.0f}점 ({' · '.join(sc['notes']) or '재무 일부 미확인'}){px}"
            elif old.get(t, {}).get("note"):
                it["note"] = old[t]["note"]
            groups[a["group"]].append(it)
        S["watchlist"] = [dict(group=g, items=groups[g]) for g in order]
        S["meta"]["selected"] = len(self.sel)
        S["meta"]["sel_list"] = sorted(self.sel)
        S["meta"]["custom"] = self.custom
        S["meta"]["host"] = "actions" if os.environ.get("GITHUB_ACTIONS") else "local"

    def _save(self):
        tmp = self.path + ".tmp"
        json.dump(self.state, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def _load_fund_cache(self):
        try:
            c = json.load(open(FUND_PATH, encoding="utf-8"))
            return c
        except Exception:
            return {}

    # ── 데이터 갱신 ──
    def refresh_daily(self):
        syms = [a["y"] for a in self.active()]
        try:
            self.daily = self.feed.daily(syms)
            self.ind = {s: tech_indicators(c) for s, c in self.daily.items()}
            self.last_daily = time.time()
            log.info("일봉 지표 갱신: %d종목", len(self.ind))
        except Exception as e:
            log.warning("일봉 갱신 실패: %s", e)

    def refresh_fundamentals(self, budget=12):
        """재무 데이터는 하루 한 번이면 충분. 한 번에 budget개씩 나눠 받는다."""
        today = now_kst().strftime("%Y-%m-%d")
        todo = [a["y"] for a in self.active() if a["y"] != "BTC-USD"
                and self.fund.get(a["y"], {}).get("_d") != today][:budget]
        for s in todo:
            try:
                f = self.feed.fundamentals(s)
                f["_d"] = today
                self.fund[s] = f
            except Exception as e:
                log.debug("재무 실패 %s: %s", s, e)
        if todo:
            json.dump(self.fund, open(FUND_PATH, "w", encoding="utf-8"), ensure_ascii=False)
            log.info("재무 데이터 갱신 %d종목", len(todo))

    def fetch_quotes(self):
        open_syms = []
        for a in self.active():
            mkt = market_of(a["y"])[0]
            if self.is_open(mkt):
                open_syms.append(a["y"])
        held = [BY_T[p["t"]]["y"] for p in self.state["positions"] if p["t"] in BY_T]
        extra = list(INDICES.values())
        syms = sorted(set(open_syms + held + extra))
        q = self.feed.live(syms)
        self.quotes.update(q)
        if "KRW=X" in q:
            self.fx = q["KRW=X"]["px"]
        return q

    def is_open(self, mkt):
        return True if self.feed.demo and mkt != "INDEX" else market_open(mkt)

    def fresh(self, y):
        q = self.quotes.get(y)
        if not q:
            return False
        if self.feed.demo:
            return True
        return time.time() - q["ts"] <= self.cfg["max_quote_age_sec"]

    # ── 계산 ──
    def fx_of(self, ccy):
        if ccy == "KRW":
            return 1.0
        if self.fx:
            return self.fx
        us = [p for p in self.state["positions"] if p.get("ccy") == "USD"]
        return us[0]["fx"] if us else 1350.0

    def equity(self):
        S = self.state
        inv = sum(p["value_krw"] for p in S["positions"])
        return round(S["cash"] + inv), inv

    def mark(self):
        for p in self.state["positions"]:
            a = BY_T.get(p["t"])
            if not a:
                continue
            q = self.quotes.get(a["y"])
            if q:
                p["px"] = round(q["px"], 4)
                p["day_pct"] = round((q["px"] / q["prev"] - 1) * 100, 2) if q.get("prev") else None
            p["fx"] = self.fx_of(p["ccy"])
            p["value_krw"] = round(p["qty"] * p["px"] * p["fx"])

    def regime(self):
        v = self.quotes.get("^VIX", {}).get("px")
        if v is None:
            v = 30.0
        if v >= 30:
            return v, "극단적 공포" if v >= 35 else "공포", self.cfg["cash_band"]["fear"]
        if v >= 20:
            return v, "경계", self.cfg["cash_band"]["caution"]
        return v, "낙관", self.cfg["cash_band"]["calm"]

    def compute_scores(self):
        out = {}
        for a in self.active():
            y = a["y"]
            if y == "BTC-USD":
                continue
            q = self.quotes.get(y)
            px = q["px"] if q else (self.daily.get(y) or [None])[-1]
            s, parts, notes = score_asset(a, self.fund.get(y, {}), self.ind.get(y), px)
            out[y] = dict(score=s, parts=parts, notes=notes, px=px, n=len(parts))
        self.scores = out
        return out

    # ── 체결 ──
    def _today_trades(self):
        d = now_kst().strftime("%Y-%m-%d")
        return [t for t in self.state["trades"] if t["date"] == d]

    def _next_id(self):
        return f"T{len(self.state['trades'])+1:04d}"

    def execute(self, side, a, qty, px, reason, signals, conf):
        S = self.state
        mkt, ccy = market_of(a["y"])
        fx = self.fx_of(ccy)
        gross = qty * px * fx
        fee = gross * self.cfg["fee_rate"]
        t = now_kst()
        tr = dict(id=self._next_id(), date=t.strftime("%Y-%m-%d"), time=t.strftime("%H:%M:%S"), side=side,
                  t=a["t"], name=a["name"], mkt=mkt, ccy=ccy, qty=qty, px=round(px, 4), fx=round(fx, 2),
                  amount_krw=round(gross), fee_krw=round(fee), reason=reason, signals=signals, conf=round(conf, 2),
                  live=not self.feed.demo)
        pos = next((p for p in S["positions"] if p["t"] == a["t"]), None)
        if side == "BUY":
            S["cash"] -= gross + fee
            if pos:
                pos["avg"] = (pos["avg"] * pos["qty"] + px * qty) / (pos["qty"] + qty)
                pos["qty"] = round(pos["qty"] + qty, 8)
                pos["cost_krw"] = round(pos["cost_krw"] + gross + fee)
            else:
                sc = self.scores.get(a["y"], {})
                S["positions"].append(dict(t=a["t"], name=a["name"], mkt=mkt, ccy=ccy, qty=qty, avg=px, px=px,
                                           fx=fx, cost_krw=round(gross + fee), value_krw=round(gross),
                                           opened=tr["date"], stop_pct=-30 if mkt == "CRYPTO" else -25,
                                           target_pct=self.cfg["target_pct"], thesis=reason, score=sc.get("score")))
        else:
            S["cash"] += gross - fee
            part = pos["cost_krw"] * qty / pos["qty"]
            tr["pnl_krw"] = round(gross - fee - part)
            pos["cost_krw"] = round(pos["cost_krw"] - part)
            pos["qty"] = round(pos["qty"] - qty, 8)
            if pos["qty"] <= 1e-9:
                S["positions"].remove(pos)
        S["trades"].append(tr)
        self.mark()
        log.info("%s %s %s @ %s — %s", side, a["name"], qty, px, reason[:60])
        return tr

    # ── 원칙 기반 판단(한 번의 틱) ──
    def decide(self):
        S, cfg = self.state, self.cfg
        eq, inv = self.equity()
        vix, regime, band = self.regime()
        cash_w = S["cash"] / eq
        today = self._today_trades()
        self.diag = dict(cash_pct=round(cash_w * 100, 1), band=[round(band[0] * 100), round(band[1] * 100)],
                         quotes=len(self.quotes), fresh=sum(1 for y in self.scores if self.fresh(y)),
                         scored=len(self.scores), candidates=0, block="")
        if len(today) >= cfg["max_trades_per_day"]:
            self.diag["block"] = "오늘 거래 한도 도달"
            return []                                   # 원칙 288
        if today and (now_kst() - datetime.fromisoformat(f"{today[-1]['date']}T{today[-1]['time']}").replace(tzinfo=KST)).total_seconds() < cfg["min_gap_sec"]:
            return []                                   # 원칙 230: 시간 분산
        traded_today = {t["t"]: t["side"] for t in today}
        done = []

        # 1) 매도 판단 — 원칙 255·257·248·263·259·22·260
        for p in list(S["positions"]):
            a = BY_T.get(p["t"])
            if not a or not self.is_open(p["mkt"]) or not self.fresh(a["y"]) or traded_today.get(p["t"]) == "BUY":
                continue
            px = self.quotes[a["y"]]["px"]
            ret = (p["value_krw"] / p["cost_krw"] - 1) * 100 if p["cost_krw"] else 0
            scd = self.scores.get(a["y"], {})
            sc = scd.get("score") if scd.get("n", 0) >= 3 else None   # 원칙 226: 데이터 없이 판단하지 않음
            if a["t"] in cfg["avoid"]:
                return [self.execute("SELL", a, p["qty"], px,
                        f"{a['name']}에 '{cfg['avoid'][a['t']]}' 문제가 있어 투자 논리를 다시 따져야 한다. 결론이 나기 전까지 보유하지 않는 것이 원칙이라 현재가 {px:,.2f}에 전량 정리했다.",
                        ["원칙 195", "원칙 255", "회계·규제 리스크"], 0.7)]
            if sc is not None and sc < cfg["thesis_break_score"]:
                return [self.execute("SELL", a, p["qty"], px,
                        f"원칙 점수가 {sc:.0f}점으로 기준({cfg['thesis_break_score']}점) 아래로 떨어졌다. 성장·수익성·밸류에이션 근거가 약해져 투자 논리가 훼손됐다고 판단해 현재가 {px:,.2f}에 전량 매도했다. 수익률 {ret:+.1f}%.",
                        ["원칙 257", "원칙 261", f"점수 {sc:.0f}"], 0.6)]
            if ret <= p["stop_pct"]:
                if sc is None or sc < cfg["emergency_keep_score"]:
                    return [self.execute("SELL", a, p["qty"], px,
                            f"원가 대비 {ret:.1f}%로 비상 점검선({p['stop_pct']}%)에 닿았고, 원칙 점수도 {sc if sc is not None else '확인 불가'}로 약하다. 영구적 자본 손실을 막기 위해 전량 매도했다.",
                            ["원칙 248", "원칙 263", "원칙 269"], 0.65)]
            th = (self.fund.get(a["y"]) or {}).get("targetHighPrice")
            last_trim = [t for t in S["trades"] if t["t"] == a["t"] and t["side"] == "SELL"]
            if th and px > th and not last_trim and p["qty"] >= 3:
                q = math.floor(p["qty"] / 3) if p["mkt"] != "CRYPTO" else round(p["qty"] / 3, 6)
                return [self.execute("SELL", a, q, px,
                        f"현재가 {px:,.2f}가 애널리스트 목표가 상단({th:,.2f})을 넘었다. 본질 가치보다 과하게 오른 구간으로 보고 1/3만 차익 실현하고 나머지는 계속 보유한다.",
                        ["원칙 259", "원칙 262", "부분 차익"], 0.55)]

        # 2) 비기술주 축소 — 원칙 22·38·260 (현금이 하한 아래일 때만, 하루 1회)
        tech_val = sum(p["value_krw"] for p in S["positions"] if BY_T.get(p["t"], {}).get("tech"))
        stock_val = max(1, inv)
        if tech_val / stock_val < cfg["min_tech_share"] and cash_w < band[0]:
            nt = [p for p in S["positions"] if not BY_T.get(p["t"], {}).get("tech") and self.is_open(p["mkt"])
                  and self.fresh(BY_T[p["t"]]["y"]) and p["t"] not in traded_today]
            if nt:
                p = min(nt, key=lambda x: self.scores.get(BY_T[x["t"]]["y"], {}).get("score", 50))
                a = BY_T[p["t"]]
                q = max(1, math.floor(p["qty"] / 3))
                px = self.quotes[a["y"]]["px"]
                return [self.execute("SELL", a, q, px,
                        f"기술 성장주 비중이 주식의 {tech_val/stock_val*100:.0f}%로 목표(70%)보다 낮고 현금도 하한 아래다. 분산용 비기술주인 {a['name']}를 1/3 줄여 더 높은 기대수익의 기술주로 옮길 재원을 만든다.",
                        ["원칙 22", "원칙 38", "원칙 260"], 0.5)]

        # 3) 매수 판단 — 원칙 3·15·39·230·231·233·234·29·249
        target_cash = band[1] if cash_w > band[1] else None
        if cash_w <= band[1]:
            self.diag["block"] = "현금 비중이 목표 범위 안"
            return done
        investable = eq * (1 - (band[0] + band[1]) / 2)
        cands = []
        for y, s in self.scores.items():
            a = BY_Y[y]
            if a["t"] not in self.sel:
                continue                                   # 사용자가 끈 종목은 새로 사지 않는다
            mkt = market_of(y)[0]
            if not self.is_open(mkt) or not self.fresh(y) or a["t"] in cfg["avoid"] or a["t"] in traded_today:  # 원칙 230: 하루 한 번씩 나눠 산다
                continue
            if s["score"] < cfg["buy_min_score"] or s.get("n", 0) < 3:   # 원칙 226·227
                continue
            q = self.quotes[y]
            day = (q["px"] / q["prev"] - 1) * 100 if q.get("prev") else 0
            if day >= cfg["no_chase_pct"]:
                continue                                   # 원칙 231
            cap = (self.fund.get(y) or {}).get("marketCap") or 0
            limit = cfg["max_weight_large"] if cap >= 1e11 else cfg["max_weight_small"]
            held = next((p for p in S["positions"] if p["t"] == a["t"]), None)
            w = (held["value_krw"] / eq) if held else 0
            tgt = min(limit, investable / eq / cfg["target_holdings"] * (1.4 if s["score"] >= 75 else 1.0))
            if w >= tgt - 0.005:
                continue
            cands.append((s["score"] + (3 if a["tech"] else 0), y, a, s, q, day, tgt, w, limit))
        # 비트코인: 위성 자산 3%, 최대 5%
        if "BTC" in self.sel and self.is_open("CRYPTO") and self.fresh("BTC-USD") and "BTC" not in traded_today:
            held = next((p for p in S["positions"] if p["t"] == "BTC"), None)
            w = held["value_krw"] / eq if held else 0
            if w < cfg["btc_target"] - 0.01:
                a = BY_T["BTC"]; q = self.quotes["BTC-USD"]
                cands.append((60, "BTC-USD", a, dict(score=None, notes=[]), q, 0, cfg["btc_target"], w, 0.05))
        self.diag["candidates"] = len(cands)
        if not cands:
            self.diag["block"] = "매수 조건(점수·추격 금지·비중)을 만족하는 종목 없음"
            return done
        cands.sort(key=lambda x: -x[0])
        pick = None
        for _, y, a, s, q, day, tgt, w, limit in cands:   # 1주도 못 사는 비싼 종목은 건너뛰고 다음 후보로
            fx = self.fx_of(market_of(y)[1])
            room = min(eq * (tgt - w), S["cash"] - eq * band[0])
            spend = min(eq * tgt / cfg["tranches"], room)
            unit = q["px"] * fx * (1 + cfg["fee_rate"])
            if a["t"] == "BTC":
                qty = round(spend / unit, 5)
                if qty * unit >= 50000:
                    pick = (y, a, s, q, day, tgt, w, qty); break
            else:
                qty = math.floor(spend / unit)
                if qty < 1 and unit <= room:
                    qty = 1                                 # 1주가 1회분보다 비싸도 목표 비중 안이면 1주
                if qty >= 1:
                    pick = (y, a, s, q, day, tgt, w, qty); break
        if not pick:
            self.diag["block"] = "후보 종목이 모두 1주 가격이 남은 매수 여력보다 비쌈"
            return done
        y, a, s, q, day, tgt, w, qty = pick
        tranche_no = 1 + len([t for t in S["trades"] if t["t"] == a["t"] and t["side"] == "BUY"])
        notes = " · ".join(s.get("notes") or []) or "재무 데이터 일부 미확인"
        ind = self.ind.get(y)
        dd = f" 52주 고점 대비 {(1-q['px']/ind['hi52'])*100:.0f}% 아래다." if ind else ""
        if a["t"] == "BTC":
            reason = (f"현재 비트코인 비중이 {w*100:.1f}%로 위성 자산 목표({cfg['btc_target']*100:.0f}%)보다 낮다. "
                      f"변동성이 큰 자산이라 상한 5% 안에서만 나눠 담는다. 현재가 ${q['px']:,.0f}.")
            sig = ["원칙 16", "원칙 249", "위성 자산"]
        else:
            reason = (f"원칙 점수 {s['score']:.0f}점({notes}).{dd} 당일 등락 {day:+.1f}%로 추격 매수 구간이 아니고, "
                      f"현금 비중 {cash_w*100:.0f}%가 {regime} 국면 목표({band[0]*100:.0f}~{band[1]*100:.0f}%)보다 높다. "
                      f"목표 비중 {tgt*100:.1f}%의 {tranche_no}차 분할 매수로 현재가 {q['px']:,.2f}에 {qty}주를 샀다. "
                      f"주가 하락만이 아니라 실적 지표를 확인한 매수이며, 점수가 {cfg['thesis_break_score']}점 아래로 떨어지면 논리 훼손으로 본다.")
            sig = ["원칙 230", "원칙 234", "원칙 5" if a["tech"] else "원칙 38", f"점수 {s['score']:.0f}"]
        conf = 0.45 + ((s["score"] or 60) - 60) / 80
        return [self.execute("BUY", a, qty, q["px"], reason, sig, clamp(conf, 0.3, 0.9))]

    # ── 화면용 상태 정리 ──
    def publish(self, trades):
        S = self.state
        t = now_kst()
        eq, inv = self.equity()
        for p in S["positions"]:
            p["weight"] = round(p["value_krw"] / eq * 100, 2)
            sc = self.scores.get(BY_T.get(p["t"], {}).get("y"), {})
            if sc:
                p["score"] = sc["score"]
        idx = {k: self.quotes.get(v, {}) for k, v in INDICES.items()}
        d = t.strftime("%Y-%m-%d")
        row = dict(date=d, equity=eq, cash=round(S["cash"]), invested=inv,
                   kospi=idx["kospi"].get("px") or S["history"][-1]["kospi"],
                   spx=idx["spx"].get("px") or S["history"][-1]["spx"],
                   ndx=idx["ndx"].get("px") or S["history"][-1]["ndx"])
        if S["history"] and S["history"][-1]["date"] == d:
            S["history"][-1] = row
        else:
            S["history"].append(row)
        S["intraday"].append(dict(ts=t.strftime("%Y-%m-%dT%H:%M:%S"), equity=eq))
        S["intraday"] = S["intraday"][-2000:]
        vix, regime, band = self.regime()
        def chg(k):
            q = idx[k]
            return round((q["px"] / q["prev"] - 1) * 100, 2) if q.get("px") and q.get("prev") else 0.0
        btc = self.quotes.get("BTC-USD", {})
        open_mk = [n for n, m in (("한국장", "KR"), ("미국장", "US")) if self.is_open(m)]
        S["market"]["regime"] = regime
        S["market"]["score"] = round(clamp(100 - (vix - 10) * 3))
        S["market"]["headline"] = (f"{'·'.join(open_mk) or '주식시장 휴장'} 실시간 운용 중 — VIX {vix:.1f}, {regime} 국면. "
                                   f"현금 목표 {band[0]*100:.0f}~{band[1]*100:.0f}%, 지금 {S['cash']/eq*100:.0f}%.")
        top = sorted(self.scores.items(), key=lambda x: -x[1]["score"])[:5]
        S["market"]["summary"] = ("원칙 점수 상위 종목: " + ", ".join(f"{BY_Y[y]['name']} {s['score']:.0f}점" for y, s in top) +
                                  ". 점수는 매출 성장·영업이익률·잉여현금흐름·부채·밸류에이션(PEG)에 선호 산업 가중치를 더해 계산한다. "
                                  "주가 하락만으로는 사지 않고, 당일 8% 넘게 급등한 종목은 추격하지 않는다.") if top else S["market"]["summary"]
        S["market"]["indicators"] = [
            dict(k="S&P 500", v=f"{row['spx']:,.2f}", c=chg("spx"), d="실시간"),
            dict(k="나스닥 종합", v=f"{row['ndx']:,.2f}", c=chg("ndx"), d="실시간"),
            dict(k="코스피", v=f"{row['kospi']:,.2f}", c=chg("kospi"), d="실시간"),
            dict(k="VIX 공포지수", v=f"{vix:.2f}", c=chg("vix"), d="실시간"),
            dict(k="원/달러", v=f"{self.fx_of('USD'):,.1f}원", c=chg("fx"), d="실시간"),
            dict(k="비트코인", v=f"${btc.get('px', 0):,.0f}", c=round((btc['px']/btc['prev']-1)*100, 2) if btc.get('prev') else 0.0, d="실시간"),
        ]
        if trades:
            buys = sum(1 for x in trades if x["side"] == "BUY")
            S["journal"].append(dict(date=d, title=f"{t.strftime('%H:%M')} {'매수' if buys else '매도'} — {trades[0]['name']}",
                                     text=trades[0]["reason"], buys=buys, sells=len(trades) - buys))
        self.rebuild_watch()
        S["meta"]["updated_at"] = t.isoformat(timespec="seconds")
        S["meta"]["day"] = len(S["history"])
        S["meta"]["feed"] = self.feed.name
        S["meta"]["diag"] = self.diag
        S["meta"]["demo"] = self.feed.demo
        S["meta"]["asof"] = dict(feed=f"시세: {self.feed.name}", tick=f"마지막 점검 {t.strftime('%m/%d %H:%M:%S')}",
                                 fx=f"원/달러 {self.fx_of('USD'):,.1f}원")
        S["live"] = {p["t"]: p.get("day_pct") for p in S["positions"]}
        self._save()

    def snapshot(self):
        with self.lock:
            return json.dumps(self.state, ensure_ascii=False)

    def tick(self):
        if time.time() - self.last_daily > 6 * 3600:
            self.refresh_daily()
        self.refresh_fundamentals()
        self.fetch_quotes()
        with self.lock:
            self.mark()
            self.compute_scores()
            trades = []
            for _ in range(2):           # 한 틱에 최대 2건(매도 후 매수 등)
                r = self.decide()
                if not r:
                    break
                trades += r
            self.publish(trades)
        return trades

    def run(self):
        while not self.stop:
            t0 = time.time()
            try:
                tr = self.tick()
                eq, _ = self.equity()
                log.info("점검 완료 · 총자산 %s원 · 거래 %d건", f"{eq:,}", len(tr))
            except Exception as e:
                log.exception("점검 중 오류: %s", e)
            any_open = market_open("KR") or market_open("US")
            wait = self.cfg["tick_seconds"] if any_open or self.feed.demo else self.cfg["idle_tick_seconds"]
            time.sleep(max(1, wait - (time.time() - t0)))
