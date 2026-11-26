"""Measure catalog readiness and actual image accessibility; never invent observations."""
import json
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
def image_ok(url):
    if not isinstance(url,str):return False
    u=urlparse(url)
    host=u.hostname or ""
    if u.scheme!="https" or not (host.endswith(".mzstatic.com") or host.endswith(".googleusercontent.com") or host.endswith(".dbankcdn.com") or host.endswith(".ggpht.com")):return False
    try:
        with urlopen(Request(url,headers={"Range":"bytes=0-1023","User-Agent":"MobileProductRadar/1.0"}),timeout=8) as r:
            return r.headers.get_content_type().startswith("image/") and bool(r.read(16))
    except Exception:return False
def metric(n,d,target):
    rate=round(n*100/d,1) if d else None
    return {"count":n,"total":d,"percent":rate,"target":target,"pass":rate>=target if rate is not None else None}
def main():
    m=json.loads((SITE/"manifest.json").read_text())
    latest=max(m["reports"],key=lambda r:r["date"],default=None)
    apps={}
    for p in (latest or {}).get("products",[]):
        if p.get("platform") not in ("App Store","Google Play","HarmonyOS") or p.get("category")=="生态":continue
        key=(p["platform"],p.get("region") or "",p.get("metadata_id") or p.get("product_id") or p["name"])
        apps.setdefault(key,p)
    rows=list(apps.values()); n=len(rows)
    urls={u for p in rows for u in [p.get("icon_url"),*(p.get("screenshots") or [])[:3]] if isinstance(u,str)}
    with ThreadPoolExecutor(max_workers=12) as pool:
        checks=dict(zip(sorted(urls),pool.map(image_ok,sorted(urls))))
    sources=sorted((ROOT/"snapshots").glob("*/*.json"))
    snap=json.loads(sources[-1].read_text()) if sources else {}
    states=snap.get("sources",{})
    fresh=snap.get("date")==datetime.now(timezone.utc).date().isoformat()
    metrics={"source_success":metric(sum(v.get("status")=="ok" for v in states.values()),len(states),85) if fresh else metric(0,0,85),"logo":metric(sum(bool(p.get("icon_url")) for p in rows),n,95),"logo_accessible":metric(sum(checks.get(p.get("icon_url"),False) for p in rows),n,95),"screenshots":metric(sum(bool(p.get("screenshots")) for p in rows),n,80),"screenshots_accessible":metric(sum(any(checks.get(u,False) for u in (p.get("screenshots") or [])[:3]) for p in rows),n,80),"developer":metric(sum(bool(p.get("developer")) for p in rows),n,95),"store_url":metric(sum(bool(p.get("store_url")) for p in rows),n,95)}
    rich=sum((p.get("completeness_score") or 0)>=80 and checks.get(p.get("icon_url"),False) and any(checks.get(u,False) for u in (p.get("screenshots") or [])[:3]) for p in rows)
    result={"checked_at":datetime.now(timezone.utc).isoformat(),"report_date":(latest or {}).get("date"),"snapshot_at":snap.get("observed_at"),"snapshot_current_utc_day":fresh,"source_status":{k:{"status":v.get("status"),"records":len(v.get("records",[]))} for k,v in states.items()},"metrics":metrics,"rich_profiles":rich,"rich_target":20,"quality":(latest or {}).get("quality",{}).get("total"),"platform_counts":{s:sum(p.get("platform")==s for p in rows) for s in ("App Store","Google Play","HarmonyOS")},"image_check_scope":"Official CDN URLs; first three screenshots per product; at least one reachable screenshot counts. Other hosts are unverified.","status":"pass" if all(v["pass"] is True for v in metrics.values()) and rich>=20 and ((latest or {}).get("quality",{}).get("total") or 0)>=85 else "needs_attention"}
    (SITE/"health.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    dest=ROOT/"metadata"/"health"
    dest.mkdir(parents=True,exist_ok=True)
    (dest/(result["checked_at"][:19].replace(":","")+"Z.json")).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
