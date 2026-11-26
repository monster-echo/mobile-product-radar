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
def image_bytes(b):
    return (b.startswith(b"\xff\xd8\xff") or b.startswith(b"\x89PNG\r\n\x1a\n") or b.startswith((b"GIF87a",b"GIF89a")) or (b[:4]==b"RIFF" and b[8:12]==b"WEBP") or (b[4:8]==b"ftyp" and b[8:12] in (b"avif",b"avis",b"heic")))
def image_ok(url):
    if not isinstance(url,str):return False
    u=urlparse(url)
    host=u.hostname or ""
    if u.scheme!="https" or not any(host==h or host.endswith("."+h) for h in ("mzstatic.com","googleusercontent.com","dbankcdn.com","ggpht.com")):return False
    for ranged in (True,False):
        headers={"User-Agent":"Mozilla/5.0","Accept":"image/avif,image/webp,image/png,image/jpeg,image/*,*/*;q=0.5"}
        if ranged:headers["Range"]="bytes=0-1023"
        try:
            with urlopen(Request(url,headers=headers),timeout=8) as r:
                if image_bytes(r.read(32)):return True
        except Exception:pass
    return False
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
    per_platform={}
    for platform in ("App Store","Google Play","HarmonyOS"):
        group=[p for p in rows if p.get("platform")==platform]
        size=len(group)
        per_platform[platform]={"total":size,"logo_accessible":metric(sum(checks.get(p.get("icon_url"),False) for p in group),size,95),"screenshots_accessible":metric(sum(any(checks.get(u,False) for u in (p.get("screenshots") or [])[:3]) for p in group),size,80),"developer":metric(sum(bool(p.get("developer")) for p in group),size,95),"store_url":metric(sum(bool(p.get("store_url")) for p in group),size,95)}
    result={"per_platform":per_platform,"checked_at":datetime.now(timezone.utc).isoformat(),"report_date":(latest or {}).get("date"),"snapshot_at":snap.get("observed_at"),"snapshot_current_utc_day":fresh,"source_status":{k:{"status":v.get("status"),"records":len(v.get("records",[]))} for k,v in states.items()},"metrics":metrics,"rich_profiles":rich,"rich_target":20,"quality":(latest or {}).get("quality",{}).get("total"),"platform_counts":{s:sum(p.get("platform")==s for p in rows) for s in ("App Store","Google Play","HarmonyOS")},"image_check_scope":"Official CDN URLs; first three screenshots per product; at least one reachable screenshot counts. Other hosts are unverified.","status":"pass" if all(v["pass"] is True for v in metrics.values()) and all(v["total"]>0 for v in per_platform.values()) and rich>=20 and ((latest or {}).get("quality",{}).get("total") or 0)>=85 else "needs_attention"}
    (SITE/"health.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    dest=ROOT/"metadata"/"health"
    dest.mkdir(parents=True,exist_ok=True)
    (dest/(result["checked_at"][:19].replace(":","")+"Z.json")).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
