"""Enrich approved catalog at build time; never overwrite historical observations.
Only exact IDs or unique exact title matches. Public source URLs, no credentials.
"""
import json, re, time, urllib.parse as U, urllib.request as R
from datetime import datetime, timezone
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/"_site/manifest.json"
def get(url):
    with R.urlopen(R.Request(url,headers={"User-Agent":"MobileProductRadar/1.0 (public app metadata)"}),timeout=12) as r:
        return r.read(4_000_000).decode("utf-8","replace")
def norm(s): return re.sub(r"[^\w]","",str(s).casefold())
def https(s): return isinstance(s,str) and s.startswith("https://")
def apple(p):
    links=[p.get("store_url","")]+p.get("source_urls",[])
    ids={m.group(1) for u in links if isinstance(u,str) for m in [re.search(r"apps\.apple\.com/[^?#]*?/id(\d+)",u)] if m}
    pid=p.get("product_id","")
    if isinstance(pid,str) and re.fullmatch(r"ios:\d+",pid): ids.add(pid.split(":")[1])
    if len(ids)>1: return {}
    region=str(p.get("region") or "US").lower()
    if region not in ("us","cn"): return {}
    if ids: params={"id":next(iter(ids)),"country":region}; endpoint="lookup"
    else: params={"term":p["name"],"entity":"software","country":region,"limit":25}; endpoint="search"
    url="https://itunes.apple.com/"+endpoint+"?"+U.urlencode(params)
    results=json.loads(get(url)).get("results",[])
    matches=[x for x in results if (str(x.get("trackId")) in ids if ids else norm(x.get("trackName"))==norm(p["name"]))]
    if len(matches)!=1: return {}
    x=matches[0]
    return {"developer":x.get("artistName"),"icon_url":x.get("artworkUrl512") or x.get("artworkUrl100"),"screenshots":x.get("screenshotUrls",[]),"store_url":x.get("trackViewUrl"),"release_date":x.get("releaseDate"),"updated_at":x.get("currentVersionReleaseDate"),"version":x.get("version"),"rating":x.get("averageUserRating"),"rating_count":x.get("userRatingCount"),"store_price":x.get("formattedPrice"),"detail_source_urls":[url],"metadata_id":"ios:"+str(x["trackId"])}
def android(p):
    from google_play_scraper import app, search
    links=[p.get("store_url","")]+p.get("source_urls",[])
    ids={U.parse_qs(U.urlparse(u).query).get("id",[""])[0] for u in links if isinstance(u,str) and U.urlparse(u).hostname=="play.google.com" and U.urlparse(u).path=="/store/apps/details"}-{""}
    if len(ids)>1:return {}
    if not ids:
        matches=[x for x in search(p["name"],lang="en",country="us",n_hits=15) if norm(x.get("title"))==norm(p["name"])]
        if len(matches)!=1:return {}
        ids={matches[0]["appId"]}
    pid=next(iter(ids)); x=app(pid,lang="en",country="us")
    if norm(x.get("title"))!=norm(p["name"]) and not p.get("store_url"):return {}
    url="https://play.google.com/store/apps/details?id="+U.quote(pid)
    return {"developer":x.get("developer"),"icon_url":x.get("icon"),"screenshots":x.get("screenshots",[]),"store_url":url,"release_date":x.get("released"),"updated_at":datetime.fromtimestamp(x["updated"],timezone.utc).isoformat() if x.get("updated") else None,"version":x.get("version"),"rating":x.get("score"),"rating_count":x.get("ratings"),"store_price":x.get("price"),"detail_source_urls":[url],"metadata_id":"android:"+pid}
class Ark(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.meta={};self.active=None;self.images=[];self.text=[];self.store=None;self.link_labels={}
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="img":
            self.images.append((a.get("alt",""),a.get("src",""),a.get("data-src","")))
            if self.active and a.get("alt"):self.link_labels.setdefault(self.active[0],set()).add(a["alt"].strip())
        if tag=="a" and U.urlparse(a.get("href","")).hostname=="appgallery.huawei.com":self.store=a["href"]
        if tag=="a" and re.fullmatch(r"/apps/[\w.%-]+/?",a.get("href","")):self.active=[a["href"],""]
        if tag=="meta":
            k=a.get("property") or a.get("name")
            if k:self.meta[k]=a.get("content","")
    def handle_data(self,d):
        if d.strip():self.text.append(d.strip())
        if self.active:self.active[1]+=d
    def handle_endtag(self,t):
        if t=="a" and self.active:self.links.append(self.active);self.active=None
def harmony(p,index):
    links=[p.get("store_url","")]+p.get("source_urls",[])+p.get("detail_source_urls",[])
    urls={u for u in links if isinstance(u,str) and re.fullmatch(r"https://fangzhou\.club/apps/[\w.%-]+/?",u)}
    if not urls:
        urls={"https://fangzhou.club"+href for href,title in index.links if norm(title)==norm(p["name"]) or any(norm(label)==norm(p["name"]) for label in index.link_labels.get(href,()))}
    if len(urls)!=1:return {}
    url=next(iter(urls)); parser=Ark();parser.feed(get(url))
    # OpenGraph image may be a social preview, not necessarily an app logo.
    # Do not classify it as icon or screenshot without explicit source semantics.
    title=parser.meta.get("og:title","")
    if title and norm(p["name"]) not in norm(title):return {}
    def field(label):
        for i,t in enumerate(parser.text):
            if t==label and i+1<len(parser.text):return parser.text[i+1]
            if t.startswith(label) and len(t)>len(label):
                value=t[len(label):].lstrip("：: ")
                if value:return value
        return None
    icon=None; shots=[]
    for alt,src,lazy in parser.images:
        image=lazy or src
        if not https(image) or U.urlparse(image).hostname not in ("appimg-drcn.dbankcdn.com","appimg-dra.dbankcdn.com","appimg-dre.dbankcdn.com"):continue
        if norm(alt)==norm(p["name"]) and "/icon" in U.urlparse(image).path:icon=image
        elif norm(p["name"]) in norm(alt) and "截图" in alt:shots.append(image)
    return {"detail_source_urls":[url],"metadata_id":"harmony:"+url.rstrip("/").split("/")[-1],"detail_status":"partial","developer":field("开发者"),"icon_url":icon,"screenshots":list(dict.fromkeys(shots)),"store_url":parser.store,"release_date":field("上架时间"),"updated_at":field("更新时间"),"version":field("版本"),"store_price":field("价格")}
def completeness(p):
    n=0
    if https(p.get("icon_url")):n+=5
    if any(https(x) for x in p.get("screenshots",[])):n+=15
    if p.get("developer"):n+=8
    if p.get("store_url"):n+=7
    if p.get("features"):n+=10
    if p.get("gameplay") or p.get("description"):n+=10
    for k in ("release_date","updated_at","version"):
        if p.get(k):n+=3 if k!="version" else 4
    if p.get("heat_evidence") and p.get("region") and p.get("chart") and p.get("source_urls"):n+=10
    if p.get("monetization"):n+=5
    if p.get("store_price") is not None or re.search(r"\$\d|¥\d",str(p.get("monetization",""))):n+=5
    if p.get("review_insights"):n+=10
    if p.get("differentiation"):n+=5
    return n
def main():
    m=json.loads(CAT.read_text()); index=Ark()
    try:index.feed(get("https://fangzhou.club/"))
    except Exception as e:print("HarmonyOS index unavailable:",type(e).__name__)
    cache={}; attempted=0; successes=0
    for report in sorted(m["reports"],key=lambda r:r["date"],reverse=True):
        for p in report["products"]:
            platform=p.get("platform")
            apple_link=any(isinstance(u,str) and "apps.apple.com/" in u and re.search(r"/id\d+",u) for u in p.get("source_urls",[]))
            kind="apple" if platform=="App Store" or (platform=="Reddit" and apple_link) else "android" if platform=="Google Play" else "harmony" if platform=="HarmonyOS" and p.get("category")!="生态" else None
            if not kind:continue
            key=(kind,p["name"],p.get("region"),p.get("product_id"),p.get("store_url"))
            if key not in cache:
                if attempted>=100:continue
                attempted+=1
                try:cache[key]=apple(p) if kind=="apple" else android(p) if kind=="android" else harmony(p,index)
                except Exception as e:print(kind,p["name"],type(e).__name__);cache[key]={}
                time.sleep(.6 if kind!="apple" else 3.1)
            x=cache[key]
            if x:
                successes+=1
                # Separate current store metadata from dated chart observations.
                for k,v in x.items():
                    if v is None or v==[] or v=="":continue
                    if k=="detail_source_urls":p[k]=list(dict.fromkeys(p.get(k,[])+v))
                    elif k in ("rating","rating_count","version","updated_at"):p["live_"+k]=v
                    else:p[k]=v
                p["metadata_observed_at"]=datetime.now(timezone.utc).isoformat()
                p["completeness_score"]=completeness({**p,**{k:p.get("live_"+k,p.get(k)) for k in ("rating","rating_count","version","updated_at")}})
                p["detail_status"]="rich" if p["completeness_score"]>=80 else "partial"
    CAT.write_text(json.dumps(m,ensure_ascii=False,indent=2))
    print("Metadata enrichment:",attempted,"attempted,",successes,"records matched")
if __name__=="__main__":main()
