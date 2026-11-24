import threading, http.server, socketserver
from playwright.sync_api import sync_playwright
from pathlib import Path
DOCS=Path('/workspace/neungnolstay-site/docs')
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(DOCS),**kw)
    def log_message(self,*a): pass
srv=socketserver.TCPServer(("127.0.0.1",0),H); port=srv.server_address[1]
threading.Thread(target=srv.serve_forever,daemon=True).start()
with sync_playwright() as pw:
    b=pw.chromium.launch(); p=b.new_page()
    reqs=[]
    p.on("requestfailed", lambda r: reqs.append(("failed", r.url[:90])))
    p.on("response", lambda r: reqs.append((r.status, r.url[:90])) if "fonts" in r.url else None)
    p.goto(f"http://127.0.0.1:{port}/ko/", wait_until="networkidle")
    p.wait_for_timeout(1500)
    print(p.evaluate("""() => ({
      cormorant: document.fonts.check('16px "Cormorant Garamond"'),
      notosans: document.fonts.check('16px "Noto Sans KR"'),
      notoserif: document.fonts.check('16px "Noto Serif KR"'),
      loaded: [...document.fonts].map(f=>f.family+':'+f.status).slice(0,10)
    })"""))
    print(reqs[:8]); b.close()
srv.shutdown()
