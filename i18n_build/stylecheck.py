import threading, http.server, socketserver, json
from playwright.sync_api import sync_playwright
from pathlib import Path
DOCS=Path('/workspace/neungnolstay-site/docs')
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(DOCS),**kw)
    def log_message(self,*a): pass
srv=socketserver.TCPServer(("127.0.0.1",0),H); port=srv.server_address[1]
threading.Thread(target=srv.serve_forever,daemon=True).start()
with sync_playwright() as pw:
    b=pw.chromium.launch(); p=b.new_page(viewport={"width":1440,"height":900})
    p.goto(f"http://127.0.0.1:{port}/ko/", wait_until="networkidle")
    print(json.dumps(p.evaluate("""() => [...document.querySelectorAll('#contact .contact-card a')].map(a => ({t:a.textContent.trim().slice(0,20), c:getComputedStyle(a).color, v:a.matches(':visited')}))"""), ensure_ascii=False, indent=1))
    b.close()
srv.shutdown()
