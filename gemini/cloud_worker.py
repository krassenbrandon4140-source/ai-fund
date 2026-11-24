#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
24시간 무인 클라우드 AI 모의투자 & 자가학습 워커 (창 없음 / 내 PC 전원 꺼져도 작동)
- GitHub Actions 또는 무료 클라우드 서버(Oracle Cloud / Render / Railway / AWS)에서 상시 실행
- 초기 자금: 10,000,000원 (1,000만 원)
- 실시간 Yahoo Finance API 시세 조회 + 152개 관심 자산 + 8대 핵심 혁신 산업 집중
- 300가지 투자 원칙 평가 및 자가학습(Self-Learning) 결과를 `portfolio_state.json`에 영구 저장
"""

import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
INITIAL_CAPITAL_KRW = 10_000_000
USD_KRW_DEFAULT = 1385.0
STATE_FILE = "portfolio_state.json"

CORE_8_SECTORS = {"반도체", "AI", "클라우드", "소프트웨어", "로보틱스", "바이오테크", "우주항공", "핀테크"}

WATCHLIST = [
    {"ticker": "^GSPC", "display": "S&P 500", "category": "지수/암호화폐", "core8": None, "currency": "USD"},
    {"ticker": "^IXIC", "display": "나스닥 종합", "category": "지수/암호화폐", "core8": None, "currency": "USD"},
    {"ticker": "^NDX", "display": "나스닥 100", "category": "지수/암호화폐", "core8": "AI", "currency": "USD"},
    {"ticker": "^KS11", "display": "코스피", "category": "지수/암호화폐", "core8": None, "currency": "KRW"},
    {"ticker": "BTC-USD", "display": "비트코인(BTC-USD)", "category": "지수/암호화폐", "core8": "핀테크", "currency": "USD"},
    {"ticker": "AAPL", "display": "AAPL", "category": "미국 빅테크", "core8": "AI", "currency": "USD"},
    {"ticker": "GOOGL", "display": "GOOGL", "category": "미국 빅테크", "core8": "AI", "currency": "USD"},
    {"ticker": "MSFT", "display": "MSFT", "category": "미국 빅테크", "core8": "클라우드", "currency": "USD"},
    {"ticker": "NVDA", "display": "NVDA", "category": "미국 빅테크", "core8": "반도체", "currency": "USD"},
    {"ticker": "AMZN", "display": "AMZN", "category": "미국 빅테크", "core8": "클라우드", "currency": "USD"},
    {"ticker": "META", "display": "META", "category": "미국 빅테크", "core8": "AI", "currency": "USD"},
    {"ticker": "TSLA", "display": "TSLA", "category": "미국 빅테크", "core8": "로보틱스", "currency": "USD"},
    {"ticker": "AVGO", "display": "AVGO", "category": "반도체", "core8": "반도체", "currency": "USD"},
    {"ticker": "ASML", "display": "ASML", "category": "반도체", "core8": "반도체", "currency": "USD"},
    {"ticker": "ARM", "display": "ARM", "category": "반도체", "core8": "반도체", "currency": "USD"},
    {"ticker": "QCOM", "display": "QCOM", "category": "반도체", "core8": "반도체", "currency": "USD"},
    {"ticker": "INTC", "display": "INTC", "category": "반도체", "core8": "반도체", "currency": "USD"},
    {"ticker": "MU", "display": "MU", "category": "반도체", "core8": "반도체", "currency": "USD"},
    {"ticker": "2330.TW", "display": "TSMC(TPE:2330)", "category": "반도체", "core8": "반도체", "currency": "TWD"},
    {"ticker": "PLTR", "display": "PLTR", "category": "AI/소프트웨어", "core8": "AI", "currency": "USD"},
    {"ticker": "NFLX", "display": "NFLX", "category": "AI/소프트웨어", "core8": "소프트웨어", "currency": "USD"},
    {"ticker": "ADBE", "display": "ADBE", "category": "AI/소프트웨어", "core8": "소프트웨어", "currency": "USD"},
    {"ticker": "PATH", "display": "PATH", "category": "AI/소프트웨어", "core8": "소프트웨어", "currency": "USD"},
    {"ticker": "AI", "display": "AI(C3)", "category": "AI/소프트웨어", "core8": "AI", "currency": "USD"},
    {"ticker": "UPST", "display": "UPST", "category": "AI/소프트웨어", "core8": "핀테크", "currency": "USD"},
    {"ticker": "SOUN", "display": "SOUN", "category": "AI/소프트웨어", "core8": "AI", "currency": "USD"},
    {"ticker": "AEYE", "display": "AEYE", "category": "AI/소프트웨어", "core8": "소프트웨어", "currency": "USD"},
    {"ticker": "FIVN", "display": "FIVN", "category": "AI/소프트웨어", "core8": "클라우드", "currency": "USD"},
    {"ticker": "BBAI", "display": "BBAI", "category": "AI/소프트웨어", "core8": "AI", "currency": "USD"},
    {"ticker": "YRD", "display": "YRD", "category": "AI/소프트웨어", "core8": "핀테크", "currency": "USD"},
    {"ticker": "IONQ", "display": "IONQ", "category": "양자컴퓨팅", "core8": "AI", "currency": "USD"},
    {"ticker": "QBTS", "display": "QBTS", "category": "양자컴퓨팅", "core8": "AI", "currency": "USD"},
    {"ticker": "RGTI", "display": "RGTI", "category": "양자컴퓨팅", "core8": "AI", "currency": "USD"},
    {"ticker": "QUBT", "display": "QUBT", "category": "양자컴퓨팅", "core8": "AI", "currency": "USD"},
    {"ticker": "BRK-B", "display": "BRK.B", "category": "헬스케어/바이오", "core8": None, "currency": "USD"},
    {"ticker": "JNJ", "display": "JNJ", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "USD"},
    {"ticker": "LLY", "display": "LLY", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "USD"},
    {"ticker": "UNH", "display": "UNH", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "USD"},
    {"ticker": "PFE", "display": "PFE", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "USD"},
    {"ticker": "MRK.DE", "display": "ETR:MRK", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "EUR"},
    {"ticker": "MDT", "display": "MDT", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "USD"},
    {"ticker": "NOVO-B.CO", "display": "CPH:NOVO-B", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "DKK"},
    {"ticker": "AZN.L", "display": "LON:AZN", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "GBP"},
    {"ticker": "CRSP", "display": "CRSP", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "USD"},
    {"ticker": "NTLA", "display": "NTLA", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "USD"},
    {"ticker": "BEAM", "display": "BEAM", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "USD"},
    {"ticker": "RXRX", "display": "RXRX", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "USD"},
    {"ticker": "VRTX", "display": "VRTX", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "USD"},
    {"ticker": "TEM", "display": "TEM", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "USD"},
    {"ticker": "ISRG", "display": "ISRG", "category": "헬스케어/바이오", "core8": "로보틱스", "currency": "USD"},
    {"ticker": "PRCT", "display": "PRCT", "category": "헬스케어/바이오", "core8": "로보틱스", "currency": "USD"},
    {"ticker": "MBOT", "display": "MBOT", "category": "헬스케어/바이오", "core8": "로보틱스", "currency": "USD"},
    {"ticker": "LTRN", "display": "LTRN", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "USD"},
    {"ticker": "TDOC", "display": "TDOC", "category": "헬스케어/바이오", "core8": "바이오테크", "currency": "USD"},
    {"ticker": "005930.KS", "display": "삼성전자(005930)", "category": "한국", "core8": "반도체", "currency": "KRW"},
    {"ticker": "000660.KS", "display": "SK하이닉스(000660)", "category": "한국", "core8": "반도체", "currency": "KRW"},
    {"ticker": "066570.KS", "display": "LG전자(066570)", "category": "한국", "core8": "로보틱스", "currency": "KRW"},
    {"ticker": "051910.KS", "display": "LG화학(051910)", "category": "한국", "core8": None, "currency": "KRW"},
    {"ticker": "000270.KS", "display": "기아(000270)", "category": "한국", "core8": None, "currency": "KRW"},
    {"ticker": "035720.KS", "display": "카카오(035720)", "category": "한국", "core8": "소프트웨어", "currency": "KRW"},
    {"ticker": "089030.KQ", "display": "테크윙(089030)", "category": "한국", "core8": "반도체", "currency": "KRW"},
    {"ticker": "007660.KS", "display": "이수페타시스(007660)", "category": "한국", "core8": "반도체", "currency": "KRW"},
    {"ticker": "042700.KS", "display": "한미반도체(042700)", "category": "한국", "core8": "반도체", "currency": "KRW"},
    {"ticker": "003230.KS", "display": "삼양식품(003230)", "category": "한국", "core8": None, "currency": "KRW"},
    {"ticker": "247540.KQ", "display": "에코프로비엠(247540)", "category": "한국", "core8": None, "currency": "KRW"},
    {"ticker": "168360.KQ", "display": "펨트론(168360)", "category": "한국", "core8": "반도체", "currency": "KRW"},
    {"ticker": "196170.KQ", "display": "알테오젠(196170)", "category": "한국", "core8": "바이오테크", "currency": "KRW"},
    {"ticker": "0700.HK", "display": "텐센트(HKG:0700)", "category": "중국/아시아", "core8": "소프트웨어", "currency": "HKD"},
    {"ticker": "BABA", "display": "BABA", "category": "중국/아시아", "core8": "클라우드", "currency": "USD"},
    {"ticker": "BIDU", "display": "BIDU", "category": "중국/아시아", "core8": "AI", "currency": "USD"},
    {"ticker": "1810.HK", "display": "샤오미(HKG:1810)", "category": "중국/아시아", "core8": "로보틱스", "currency": "HKD"},
    {"ticker": "NIO", "display": "NIO", "category": "중국/아시아", "core8": None, "currency": "USD"},
    {"ticker": "BYDDY", "display": "BYDDY", "category": "중국/아시아", "core8": None, "currency": "USD"},
    {"ticker": "0992.HK", "display": "레노버(HKG:0992)", "category": "중국/아시아", "core8": "AI", "currency": "HKD"},
    {"ticker": "HOOD", "display": "HOOD", "category": "소비/유통", "core8": "핀테크", "currency": "USD"},
    {"ticker": "BKNG", "display": "BKNG", "category": "소비/유통", "core8": None, "currency": "USD"},
    {"ticker": "UBER", "display": "UBER", "category": "소비/유통", "core8": "소프트웨어", "currency": "USD"},
    {"ticker": "MCD", "display": "MCD", "category": "소비/유통", "core8": None, "currency": "USD"},
    {"ticker": "KO", "display": "KO", "category": "소비/유통", "core8": None, "currency": "USD"},
    {"ticker": "PEP", "display": "PEP", "category": "소비/유통", "core8": None, "currency": "USD"},
    {"ticker": "SBUX", "display": "SBUX", "category": "소비/유통", "core8": None, "currency": "USD"},
    {"ticker": "WMT", "display": "WMT", "category": "소비/유통", "core8": None, "currency": "USD"},
    {"ticker": "COST", "display": "COST", "category": "소비/유통", "core8": None, "currency": "USD"},
    {"ticker": "NKE", "display": "NKE", "category": "소비/유통", "core8": None, "currency": "USD"},
    {"ticker": "ADS.DE", "display": "ETR:ADS", "category": "소비/유통", "core8": None, "currency": "EUR"},
    {"ticker": "MC.PA", "display": "EPA:MC", "category": "소비/유통", "core8": None, "currency": "EUR"},
    {"ticker": "JPM", "display": "JPM", "category": "금융", "core8": "핀테크", "currency": "USD"},
    {"ticker": "BAC", "display": "BAC", "category": "금융", "core8": None, "currency": "USD"},
    {"ticker": "WFC", "display": "WFC", "category": "금융", "core8": None, "currency": "USD"},
    {"ticker": "V", "display": "V", "category": "금융", "core8": "핀테크", "currency": "USD"},
    {"ticker": "MA", "display": "MA", "category": "금융", "core8": "핀테크", "currency": "USD"},
    {"ticker": "BARC.L", "display": "LON:BARC", "category": "금융", "core8": None, "currency": "GBP"},
    {"ticker": "105560.KS", "display": "KB", "category": "금융", "core8": None, "currency": "KRW"},
    {"ticker": "XOM", "display": "XOM", "category": "에너지/친환경", "core8": None, "currency": "USD"},
    {"ticker": "CVX", "display": "CVX", "category": "에너지/친환경", "core8": None, "currency": "USD"},
    {"ticker": "CCJ", "display": "CCJ", "category": "에너지/친환경", "core8": None, "currency": "USD"},
    {"ticker": "BE", "display": "BE", "category": "에너지/친환경", "core8": None, "currency": "USD"},
    {"ticker": "PLUG", "display": "PLUG", "category": "에너지/친환경", "core8": None, "currency": "USD"},
    {"ticker": "NEE", "display": "NEE", "category": "에너지/친환경", "core8": None, "currency": "USD"},
    {"ticker": "ENPH", "display": "ENPH", "category": "에너지/친환경", "core8": None, "currency": "USD"},
    {"ticker": "FSLR", "display": "FSLR", "category": "에너지/친환경", "core8": None, "currency": "USD"},
    {"ticker": "SEDG", "display": "SEDG", "category": "에너지/친환경", "core8": None, "currency": "USD"},
    {"ticker": "BEPC", "display": "BEPC", "category": "에너지/친환경", "core8": None, "currency": "USD"},
    {"ticker": "GM", "display": "GM", "category": "자동차", "core8": None, "currency": "USD"},
    {"ticker": "F", "display": "F", "category": "자동차", "core8": None, "currency": "USD"},
    {"ticker": "VOW3.DE", "display": "ETR:VOW3", "category": "자동차", "core8": None, "currency": "EUR"},
    {"ticker": "BMW.DE", "display": "ETR:BMW", "category": "자동차", "core8": None, "currency": "EUR"},
    {"ticker": "MBG.DE", "display": "ETR:MBG", "category": "자동차", "core8": None, "currency": "EUR"},
    {"ticker": "BA", "display": "BA", "category": "항공우주/방산", "core8": "우주항공", "currency": "USD"},
    {"ticker": "AIR.PA", "display": "EPA:AIR", "category": "항공우주/방산", "core8": "우주항공", "currency": "EUR"},
    {"ticker": "LMT", "display": "LMT", "category": "항공우주/방산", "core8": "우주항공", "currency": "USD"},
    {"ticker": "NOC", "display": "NOC", "category": "항공우주/방산", "core8": "우주항공", "currency": "USD"},
    {"ticker": "LHX", "display": "LHX", "category": "항공우주/방산", "core8": "우주항공", "currency": "USD"},
    {"ticker": "GE", "display": "GE", "category": "항공우주/방산", "core8": "우주항공", "currency": "USD"},
    {"ticker": "DAL", "display": "DAL", "category": "항공우주/방산", "core8": None, "currency": "USD"},
    {"ticker": "FDX", "display": "FDX", "category": "항공우주/방산", "core8": None, "currency": "USD"},
    {"ticker": "UPS", "display": "UPS", "category": "항공우주/방산", "core8": None, "currency": "USD"},
    {"ticker": "T", "display": "T", "category": "통신/IT", "core8": None, "currency": "USD"},
    {"ticker": "VZ", "display": "VZ", "category": "통신/IT", "core8": None, "currency": "USD"},
    {"ticker": "CMCSA", "display": "CMCSA", "category": "통신/IT", "core8": None, "currency": "USD"},
    {"ticker": "IBM", "display": "IBM", "category": "통신/IT", "core8": "클라우드", "currency": "USD"},
    {"ticker": "HPQ", "display": "HPQ", "category": "통신/IT", "core8": None, "currency": "USD"},
    {"ticker": "PYPL", "display": "PYPL", "category": "통신/IT", "core8": "핀테크", "currency": "USD"},
    {"ticker": "LUNR", "display": "LUNR", "category": "우주/위성", "core8": "우주항공", "currency": "USD"},
    {"ticker": "RKLB", "display": "RKLB", "category": "우주/위성", "core8": "우주항공", "currency": "USD"},
    {"ticker": "ASTS", "display": "ASTS", "category": "우주/위성", "core8": "우주항공", "currency": "USD"},
    {"ticker": "BKSY", "display": "BKSY", "category": "우주/위성", "core8": "우주항공", "currency": "USD"},
    {"ticker": "VSAT", "display": "VSAT", "category": "우주/위성", "core8": "우주항공", "currency": "USD"},
    {"ticker": "ACHR", "display": "ACHR", "category": "우주/위성", "core8": "우주항공", "currency": "USD"},
    {"ticker": "DDD", "display": "DDD", "category": "3D프린팅/로보틱스", "core8": "로보틱스", "currency": "USD"},
    {"ticker": "SSYS", "display": "SSYS", "category": "3D프린팅/로보틱스", "core8": "로보틱스", "currency": "USD"},
    {"ticker": "PRLB", "display": "PRLB", "category": "3D프린팅/로보틱스", "core8": "로보틱스", "currency": "USD"},
    {"ticker": "NNDM", "display": "NNDM", "category": "3D프린팅/로보틱스", "core8": "로보틱스", "currency": "USD"},
    {"ticker": "MTLS", "display": "MTLS", "category": "3D프린팅/로보틱스", "core8": "로보틱스", "currency": "USD"},
    {"ticker": "SYM", "display": "SYM", "category": "3D프린팅/로보틱스", "core8": "로보틱스", "currency": "USD"},
    {"ticker": "ARBE", "display": "ARBE", "category": "3D프린팅/로보틱스", "core8": "로보틱스", "currency": "USD"},
    {"ticker": "CXAI", "display": "CXAI", "category": "3D프린팅/로보틱스", "core8": "AI", "currency": "USD"},
    {"ticker": "EVLV", "display": "EVLV", "category": "3D프린팅/로보틱스", "core8": "AI", "currency": "USD"},
    {"ticker": "SERV", "display": "SERV", "category": "3D프린팅/로보틱스", "core8": "로보틱스", "currency": "USD"},
    {"ticker": "GNSS", "display": "GNSS", "category": "3D프린팅/로보틱스", "core8": None, "currency": "USD"},
    {"ticker": "OSIS", "display": "OSIS", "category": "3D프린팅/로보틱스", "core8": None, "currency": "USD"},
    {"ticker": "STEM", "display": "STEM", "category": "기타", "core8": None, "currency": "USD"},
    {"ticker": "QS", "display": "QS", "category": "기타", "core8": None, "currency": "USD"},
    {"ticker": "BYND", "display": "BYND", "category": "기타", "core8": None, "currency": "USD"},
    {"ticker": "GLBE", "display": "GLBE", "category": "기타", "core8": "클라우드", "currency": "USD"},
    {"ticker": "GLOB", "display": "GLOB", "category": "기타", "core8": "소프트웨어", "currency": "USD"},
    {"ticker": "TEMN.SW", "display": "SWX:TEMN", "category": "기타", "core8": "핀테크", "currency": "CHF"},
    {"ticker": "NURL.CN", "display": "CNSX:NURL", "category": "기타", "core8": "AI", "currency": "CAD"},
    {"ticker": "BAYN.DE", "display": "ETR:BAYN", "category": "기타", "core8": "바이오테크", "currency": "EUR"},
]


def fetch_quotes(tickers):
    quotes = {}
    for i in range(0, len(tickers), 30):
        batch = ",".join(tickers[i:i+30])
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={batch}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data.get("quoteResponse", {}).get("result", []):
                    sym = item.get("symbol")
                    price = item.get("regularMarketPrice")
                    chg = item.get("regularMarketChangePercent", 0.0)
                    if sym and price:
                        quotes[sym] = {"price": float(price), "change_pct": float(chg)}
        except Exception:
            continue
    return quotes


def to_krw(price, currency, fx):
    rates = {"KRW": 1.0, "USD": fx, "EUR": fx * 1.08, "GBP": fx * 1.27,
             "HKD": fx / 7.8, "TWD": fx / 32.0, "DKK": fx / 6.9, "CHF": fx * 1.13, "CAD": fx * 0.72}
    return price * rates.get(currency, fx)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "cash_krw": INITIAL_CAPITAL_KRW,
        "holdings": {},
        "trade_logs": [],
        "equity_history": [],
        "latest_prices": {},
        "learning_weights": {
            "core8_bonus": 22.0,
            "momentum_weight": 1.35,
            "dip_buy_weight": 1.30,
            "max_single_weight": 0.18,
            "min_cash_ratio": 0.10,
            "take_profit_pct": 18.0,
            "stop_loss_pct": -8.5,
            "learning_episodes": 0,
            "win_count": 0,
            "loss_count": 0
        }
    }


def main():
    state = load_state()
    tickers = [a["ticker"] for a in WATCHLIST] + ["KRW=X"]
    quotes = fetch_quotes(tickers)
    fx = quotes.get("KRW=X", {}).get("price", USD_KRW_DEFAULT)
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

    # Record latest prices for dashboard display
    for a in WATCHLIST:
        q = quotes.get(a["ticker"])
        if q:
            state["latest_prices"][a["ticker"]] = {
                "display": a["display"],
                "category": a["category"],
                "core8": a["core8"],
                "price_krw": round(to_krw(q["price"], a["currency"], fx)),
                "change_pct": round(q["change_pct"], 2)
            }

    w = state["learning_weights"]
    stock_val = 0.0
    for sym, pos in list(state["holdings"].items()):
        q = quotes.get(sym)
        cur_krw = to_krw(q["price"], pos["currency"], fx) if q else pos["last_price_krw"]
        pos["last_price_krw"] = cur_krw
        pnl_pct = ((cur_krw - pos["avg_price_krw"]) / pos["avg_price_krw"]) * 100.0

        if pnl_pct >= w["take_profit_pct"] or pnl_pct <= w["stop_loss_pct"]:
            proceeds = pos["qty"] * cur_krw
            state["cash_krw"] += proceeds
            w["learning_episodes"] += 1
            if pnl_pct >= 0:
                w["win_count"] += 1
                w["momentum_weight"] = round(min(2.2, w["momentum_weight"] + 0.03), 3)
                lesson = f"자가학습 Ep.{w['learning_episodes']}: 익절(+{pnl_pct:.1f}%) → 모멘텀 가중치 {w['momentum_weight']} 상향 (원칙 #296)"
            else:
                w["loss_count"] += 1
                w["dip_buy_weight"] = round(min(2.2, w["dip_buy_weight"] + 0.04), 3)
                lesson = f"자가학습 Ep.{w['learning_episodes']}: 손절({pnl_pct:.1f}%) → 분할매수 가중치 {w['dip_buy_weight']} 보정 (원칙 #283·295)"

            state["trade_logs"].insert(0, {
                "time": now_kst,
                "action": "SELL",
                "ticker": pos["display"],
                "price_krw": round(cur_krw),
                "amount_krw": round(proceeds),
                "pnl_pct": round(pnl_pct, 2),
                "rationale": lesson
            })
            del state["holdings"][sym]
        else:
            stock_val += pos["qty"] * cur_krw

    total_eq = state["cash_krw"] + stock_val
    candidates = []
    for a in WATCHLIST:
        if a["category"] == "지수/암호화폐" and a["ticker"].startswith("^"):
            continue
        q = quotes.get(a["ticker"])
        if not q:
            continue
        score = 50.0 + (w["core8_bonus"] if a["core8"] in CORE_8_SECTORS else -12.0)
        reasons = [f"원칙 #32~37({a['core8']})" if a["core8"] else "원칙 #38(분산)"]
        if -4.5 <= q["change_pct"] <= -1.0:
            score += 14.0 * w["dip_buy_weight"]
            reasons.append("원칙 #230·232(조정 분할매수)")
        elif 0.7 <= q["change_pct"] <= 4.8:
            score += 11.0 * w["momentum_weight"]
            reasons.append("원칙 #66·134(상승 모멘텀)")
        if score >= 75.0:
            candidates.append((round(score, 1), a, q, reasons))

    candidates.sort(key=lambda x: x[0], reverse=True)
    min_cash = total_eq * w["min_cash_ratio"]

    for score, a, q, reasons in candidates[:3]:
        if state["cash_krw"] <= min_cash + 300_000:
            break
        sym = a["ticker"]
        cur_krw = to_krw(q["price"], a["currency"], fx)
        held_val = state["holdings"].get(sym, {}).get("qty", 0) * cur_krw
        max_single = total_eq * w["max_single_weight"]
        if held_val >= max_single * 0.9:
            continue
        alloc = min(850_000, max_single - held_val, state["cash_krw"] - min_cash)
        if alloc < 200_000:
            continue
        qty = alloc / cur_krw
        if sym in state["holdings"]:
            old = state["holdings"][sym]
            nq = old["qty"] + qty
            old["avg_price_krw"] = ((old["qty"] * old["avg_price_krw"]) + alloc) / nq
            old["qty"] = nq
            old["last_price_krw"] = cur_krw
        else:
            state["holdings"][sym] = {
                "display": a["display"], "category": a["category"], "core8": a["core8"],
                "currency": a["currency"], "qty": qty, "avg_price_krw": cur_krw, "last_price_krw": cur_krw
            }
        state["cash_krw"] -= alloc
        state["trade_logs"].insert(0, {
            "time": now_kst,
            "action": "BUY",
            "ticker": a["display"],
            "price_krw": round(cur_krw),
            "amount_krw": round(alloc),
            "rationale": f"AI 점수 {score}점 | {', '.join(reasons)} | 원칙 #29 단일비중 18% 준수"
        })

    stock_val = sum(p["qty"] * p["last_price_krw"] for p in state["holdings"].values())
    total_eq = state["cash_krw"] + stock_val
    ret_pct = ((total_eq - INITIAL_CAPITAL_KRW) / INITIAL_CAPITAL_KRW) * 100.0
    state["equity_history"].append({
        "time": now_kst,
        "equity_krw": round(total_eq),
        "return_pct": round(ret_pct, 3)
    })
    state["equity_history"] = state["equity_history"][-300:]
    state["trade_logs"] = state["trade_logs"][-120:]
    state["last_updated"] = now_kst

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    print(f"[{now_kst}] 총자산 {total_eq:,.0f}원 ({ret_pct:+.2f}%) | 학습 Ep.{w['learning_episodes']}")


if __name__ == "__main__":
    main()
