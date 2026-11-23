# 관심 자산 목록 → 야후 파이낸스 심볼 매핑
# (관심목록 표시용 티커, 야후 심볼, 이름, 그룹, 선호 산업 여부)
# 선호 산업: 반도체, AI, 클라우드, 소프트웨어, 로보틱스, 바이오테크, 우주항공, 핀테크

RAW = """
지수/암호화폐|^GSPC|^GSPC|S&P 500|0
지수/암호화폐|^IXIC|^IXIC|나스닥 종합|0
지수/암호화폐|^NDX|^NDX|나스닥 100|0
지수/암호화폐|^KS11|^KS11|코스피|0
지수/암호화폐|BTC|BTC-USD|비트코인|1
미국 빅테크|AAPL|AAPL|애플|1
미국 빅테크|GOOGL|GOOGL|알파벳|1
미국 빅테크|MSFT|MSFT|마이크로소프트|1
미국 빅테크|NVDA|NVDA|엔비디아|1
미국 빅테크|AMZN|AMZN|아마존|1
미국 빅테크|META|META|메타|1
미국 빅테크|TSLA|TSLA|테슬라|1
반도체|AVGO|AVGO|브로드컴|1
반도체|ASML|ASML|ASML|1
반도체|ARM|ARM|Arm|1
반도체|QCOM|QCOM|퀄컴|1
반도체|INTC|INTC|인텔|1
반도체|MU|MU|마이크론|1
반도체|TPE:2330|2330.TW|TSMC|1
AI/소프트웨어|PLTR|PLTR|팔란티어|1
AI/소프트웨어|NFLX|NFLX|넷플릭스|1
AI/소프트웨어|ADBE|ADBE|어도비|1
AI/소프트웨어|PATH|PATH|유아이패스|1
AI/소프트웨어|AI|AI|C3.ai|1
AI/소프트웨어|UPST|UPST|업스타트|1
AI/소프트웨어|SOUN|SOUN|사운드하운드|1
AI/소프트웨어|AEYE|AEYE|AEye|1
AI/소프트웨어|FIVN|FIVN|Five9|1
AI/소프트웨어|BBAI|BBAI|빅베어AI|1
AI/소프트웨어|YRD|YRD|Yiren Digital|1
양자컴퓨팅|IONQ|IONQ|아이온큐|1
양자컴퓨팅|QBTS|QBTS|D-Wave|1
양자컴퓨팅|RGTI|RGTI|리게티|1
양자컴퓨팅|QUBT|QUBT|퀀텀 컴퓨팅|1
헬스케어/바이오|BRK.B|BRK-B|버크셔 해서웨이 B|0
헬스케어/바이오|JNJ|JNJ|존슨앤드존슨|0
헬스케어/바이오|LLY|LLY|일라이 릴리|1
헬스케어/바이오|UNH|UNH|유나이티드헬스|0
헬스케어/바이오|PFE|PFE|화이자|0
헬스케어/바이오|ETR:MRK|MRK.DE|머크 KGaA|0
헬스케어/바이오|MDT|MDT|메드트로닉|0
헬스케어/바이오|CPH:NOVO-B|NOVO-B.CO|노보 노디스크|1
헬스케어/바이오|LON:AZN|AZN.L|아스트라제네카|0
헬스케어/바이오|CRSP|CRSP|크리스퍼|1
헬스케어/바이오|NTLA|NTLA|인텔리아|1
헬스케어/바이오|BEAM|BEAM|빔 테라퓨틱스|1
헬스케어/바이오|RXRX|RXRX|리커전|1
헬스케어/바이오|VRTX|VRTX|버텍스|1
헬스케어/바이오|TEM|TEM|템퍼스 AI|1
헬스케어/바이오|ISRG|ISRG|인튜이티브 서지컬|1
헬스케어/바이오|PRCT|PRCT|프로셉트|1
헬스케어/바이오|MBOT|MBOT|마이크로봇|1
헬스케어/바이오|LTRN|LTRN|랜턴 파마|1
헬스케어/바이오|TDOC|TDOC|텔라닥|1
한국|005930|005930.KS|삼성전자|1
한국|000660|000660.KS|SK하이닉스|1
한국|066570|066570.KS|LG전자|0
한국|051910|051910.KS|LG화학|0
한국|000270|000270.KS|기아|0
한국|035720|035720.KS|카카오|1
한국|089030|089030.KQ|테크윙|1
한국|007660|007660.KS|이수페타시스|1
한국|042700|042700.KS|한미반도체|1
한국|003230|003230.KS|삼양식품|0
한국|247540|247540.KQ|에코프로비엠|0
한국|168360|168360.KQ|펨트론|1
한국|196170|196170.KQ|알테오젠|1
중국/아시아|HKG:0700|0700.HK|텐센트|1
중국/아시아|BABA|BABA|알리바바|1
중국/아시아|BIDU|BIDU|바이두|1
중국/아시아|HKG:1810|1810.HK|샤오미|1
중국/아시아|NIO|NIO|니오|0
중국/아시아|BYDDY|BYDDY|BYD|0
중국/아시아|HKG:0992|0992.HK|레노버|1
소비/유통|HOOD|HOOD|로빈후드|1
소비/유통|BKNG|BKNG|부킹|0
소비/유통|UBER|UBER|우버|1
소비/유통|MCD|MCD|맥도날드|0
소비/유통|KO|KO|코카콜라|0
소비/유통|PEP|PEP|펩시코|0
소비/유통|SBUX|SBUX|스타벅스|0
소비/유통|WMT|WMT|월마트|0
소비/유통|COST|COST|코스트코|0
소비/유통|NKE|NKE|나이키|0
소비/유통|ETR:ADS|ADS.DE|아디다스|0
소비/유통|EPA:MC|MC.PA|LVMH|0
금융|JPM|JPM|JP모건|0
금융|BAC|BAC|뱅크오브아메리카|0
금융|WFC|WFC|웰스파고|0
금융|V|V|비자|1
금융|MA|MA|마스터카드|1
금융|LON:BARC|BARC.L|바클레이즈|0
금융|KB|KB|KB금융|0
에너지/친환경|XOM|XOM|엑슨모빌|0
에너지/친환경|CVX|CVX|셰브론|0
에너지/친환경|CCJ|CCJ|카메코|0
에너지/친환경|BE|BE|블룸에너지|0
에너지/친환경|PLUG|PLUG|플러그파워|0
에너지/친환경|NEE|NEE|넥스트에라|0
에너지/친환경|ENPH|ENPH|엔페이즈|0
에너지/친환경|FSLR|FSLR|퍼스트솔라|0
에너지/친환경|SEDG|SEDG|솔라엣지|0
에너지/친환경|BEPC|BEPC|브룩필드 리뉴어블|0
자동차|GM|GM|GM|0
자동차|F|F|포드|0
자동차|ETR:VOW3|VOW3.DE|폭스바겐|0
자동차|ETR:BMW|BMW.DE|BMW|0
자동차|ETR:MBG|MBG.DE|메르세데스-벤츠|0
항공우주/방산|BA|BA|보잉|1
항공우주/방산|EPA:AIR|AIR.PA|에어버스|1
항공우주/방산|LMT|LMT|록히드마틴|1
항공우주/방산|NOC|NOC|노스롭그루먼|1
항공우주/방산|LHX|LHX|L3해리스|1
항공우주/방산|GE|GE|GE에어로스페이스|1
항공우주/방산|DAL|DAL|델타항공|0
항공우주/방산|FDX|FDX|페덱스|0
항공우주/방산|UPS|UPS|UPS|0
통신/IT|T|T|AT&T|0
통신/IT|VZ|VZ|버라이즌|0
통신/IT|CMCSA|CMCSA|컴캐스트|0
통신/IT|IBM|IBM|IBM|1
통신/IT|HPQ|HPQ|HP|0
통신/IT|PYPL|PYPL|페이팔|1
우주/위성|SPCX|SPCX|스페이스X|1
우주/위성|LUNR|LUNR|인튜이티브 머신스|1
우주/위성|RKLB|RKLB|로켓랩|1
우주/위성|ASTS|ASTS|AST 스페이스모바일|1
우주/위성|BKSY|BKSY|블랙스카이|1
우주/위성|VSAT|VSAT|비아샛|1
우주/위성|ACHR|ACHR|아처 에비에이션|1
3D프린팅/로보틱스|DDD|DDD|3D시스템즈|1
3D프린팅/로보틱스|SSYS|SSYS|스트라타시스|1
3D프린팅/로보틱스|PRLB|PRLB|프로토랩스|1
3D프린팅/로보틱스|NNDM|NNDM|나노디멘션|1
3D프린팅/로보틱스|MTLS|MTLS|머티리얼라이즈|1
3D프린팅/로보틱스|SYM|SYM|심보틱|1
3D프린팅/로보틱스|ARBE|ARBE|아르베 로보틱스|1
3D프린팅/로보틱스|CXAI|CXAI|CXApp|1
3D프린팅/로보틱스|EVLV|EVLV|이볼브|1
3D프린팅/로보틱스|SERV|SERV|서브 로보틱스|1
3D프린팅/로보틱스|GNSS|GNSS|제네시스|1
3D프린팅/로보틱스|OSIS|OSIS|OSI 시스템즈|1
기타|STEM|STEM|스템|0
기타|QS|QS|퀀텀스케이프|0
기타|BYND|BYND|비욘드미트|0
기타|GLBE|GLBE|글로벌-e|1
기타|GLOB|GLOB|글로반트|1
기타|SWX:TEMN|TEMN.SW|테메노스|1
기타|CNSX:NURL|NURL.CN|뉴럴리|1
기타|ETR:BAYN|BAYN.DE|바이엘|0
"""

ASSETS = []
for line in RAW.strip().splitlines():
    g, t, y, n, tech = line.split("|")
    ASSETS.append(dict(group=g, t=t, y=y, name=n, tech=tech == "1"))

BY_Y = {a["y"]: a for a in ASSETS}
BY_T = {a["t"]: a for a in ASSETS}


def market_of(y):
    """심볼 → (시장코드, 통화). 거래 가능한 시장은 US / KR / CRYPTO."""
    if y.startswith("^"):
        return "INDEX", None
    if y == "BTC-USD":
        return "CRYPTO", "USD"
    if y.endswith(".KS") or y.endswith(".KQ"):
        return "KR", "KRW"
    if "." in y and not y.endswith(".B"):
        return "OTHER", None  # 해외(유럽·홍콩·대만 등): 관찰만
    return "US", "USD"


TRADABLE = [a for a in ASSETS if market_of(a["y"])[0] in ("US", "KR", "CRYPTO")]
INDICES = {"spx": "^GSPC", "ndx": "^IXIC", "kospi": "^KS11", "vix": "^VIX", "fx": "KRW=X"}


def add_custom(y, name, tech, group="내가 추가한 종목"):
    """사용자가 직접 추가한 종목을 목록에 넣는다. 거래 가능한 시장(US/KR/CRYPTO)만 매매 대상."""
    t = y.split(".")[0] if (y.endswith(".KS") or y.endswith(".KQ")) else y
    if y in BY_Y:
        return BY_Y[y]
    a = dict(group=group, t=t, y=y, name=name or t, tech=bool(tech), custom=True)
    ASSETS.append(a); BY_Y[y] = a; BY_T[t] = a
    if market_of(y)[0] in ("US", "KR", "CRYPTO"):
        TRADABLE.append(a)
    return a


def remove_custom(t):
    a = BY_T.get(t)
    if not a or not a.get("custom"):
        return False
    ASSETS.remove(a); BY_Y.pop(a["y"], None); BY_T.pop(t, None)
    if a in TRADABLE:
        TRADABLE.remove(a)
    return True
