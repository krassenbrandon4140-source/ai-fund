"""AI 펀드 1000 실시간 모의투자 — 실행 파일.

  python app.py          실제 시세로 실시간 모의투자
  python app.py --demo   가짜 시세로 화면과 규칙만 시험
"""
import argparse, json, logging, os, sys, threading, webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import Engine, HERE, load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
ENGINE = None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=os.path.join(HERE, "static"), **k)

    def log_message(self, *a):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/data/portfolio.json":
            return self._send(ENGINE.snapshot().encode("utf-8"), "application/json")
        if path == "/data/principles.json":
            return self._send(open(os.path.join(HERE, "data", "principles.json"), "rb").read(), "application/json")
        return super().do_GET()

    def do_POST(self):
        """관찰 대상 선택·종목 추가/삭제. 이 컴퓨터(127.0.0.1)에서만 받는다."""
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            path = self.path.split("?")[0]
            if path == "/api/select":
                cnt = ENGINE.set_selected(list(body.get("t", [])), bool(body.get("on")))
                res = dict(ok=True, selected=cnt)
            elif path == "/api/custom":
                a = ENGINE.add_custom(str(body.get("y", "")), str(body.get("name", ""))[:30], bool(body.get("tech", True)))
                res = dict(ok=True, t=a["t"], name=a["name"])
            elif path == "/api/custom/remove":
                ENGINE.remove_custom(str(body.get("t", "")))
                res = dict(ok=True)
            else:
                self.send_error(404); return
        except ValueError as e:
            res = dict(ok=False, error=str(e))
        except Exception as e:
            logging.exception("요청 처리 실패")
            res = dict(ok=False, error="처리 중 오류가 났습니다.")
        self._send(json.dumps(res, ensure_ascii=False).encode("utf-8"), "application/json")

    def _send(self, body, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    global ENGINE
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="가짜 시세로 시험 실행")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--once", action="store_true", help="한 번만 점검하고 종료(시험용)")
    args = ap.parse_args()
    ENGINE = Engine(demo=args.demo)
    if args.once:
        ENGINE.refresh_fundamentals(budget=40)
        tr = ENGINE.tick()
        print("거래", len(tr), "건 · 총자산", ENGINE.equity()[0])
        return
    port = load_config()["port"]
    threading.Thread(target=ENGINE.run, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"\n  AI 펀드 1000 실시간 모의투자 실행 중 → {url}\n  ({ENGINE.feed.name}) 끄려면 Ctrl+C\n")
    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        ENGINE.stop = True
        print("종료합니다. 운용 기록은 data/portfolio.json에 저장돼 있습니다.")


if __name__ == "__main__":
    main()
