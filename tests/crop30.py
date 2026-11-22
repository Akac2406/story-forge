import os as _os,sys as _sys
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.normpath(_os.path.join(HERE,"..","site"));FIX=_os.path.join(HERE,"fixtures")
import sys,subprocess,time as _t,base64,json
from playwright.sync_api import sync_playwright
W=sys.argv[1]
srv=subprocess.Popen([_sys.executable,"-m","http.server","8793","--bind","127.0.0.1"],cwd=APP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);_t.sleep(1)
with sync_playwright() as p:
    br=p.chromium.launch(args=["--no-sandbox"]);pg=br.new_page();pg.goto("http://127.0.0.1:8793/index.html");pg.wait_for_selector(".cta")
    for i in range(1,11):
        u="data:image/png;base64,"+base64.b64encode(open(f"{FIX}/shots/s{i}.png","rb").read()).decode()
        r=pg.evaluate("async u=>{const c=await shotCrops(u);return c.map(x=>({url:x.url,y:x.y,h:x.h}))}",u)
        print(f"shot {i}:",[(round(x['y'],2),round(x['h'],2)) for x in r])
        for k,x in enumerate(r): open(f"{W}/crops/s{i}_{k}.jpg","wb").write(base64.b64decode(x["url"].split(",")[1]))
    br.close()
srv.terminate()

print("ERRORS: []")
