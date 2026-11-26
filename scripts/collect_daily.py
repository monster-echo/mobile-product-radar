"""Collect public discovery signals. These are observations, not reviewed reports."""
import json, re
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor
from enrich_catalog import get, Ark
ROOT=Path(__file__).resolve().parents[1]
NOW=datetime.now(timezone.utc).isoformat()
DAY=NOW[:10]
def j(url):return json.loads(get(url))
def apple(region,kind):
    url=f"https://rss.applemarketingtools.com/api/v2/{region}/{kind}/top-free/50/{kind}.json"
    rows=j(url)["feed"]["results"]
    return [{"name":x["name"],"product_id":"ios:"+x["id"],"developer":x.get("artistName"),"icon_url":x.get("artworkUrl100"),"store_url":x.get("url"),"release_date":x.get("releaseDate"),"rank":i,"region":region.upper(),"chart":kind+" top-free","source_url":url} for i,x in enumerate(rows,1)]
def hf(kind):
    url="https://huggingface.co/api/"+kind+"?"+urlencode({"sort":"trendingScore","direction":-1,"limit":30})
    return [{"name":x["id"],"likes":x.get("likes"),"downloads":x.get("downloads"),"source_url":"https://huggingface.co/"+("spaces/" if kind=="spaces" else "")+x["id"],"signal":"API trending response"} for x in j(url)]
def hn():
    base="https://hacker-news.firebaseio.com/v0/"
    ids=j(base+"showstories.json")[:30]
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows=list(pool.map(lambda i:j(base+"item/"+str(i)+".json"),ids))
    return [{"name":x["title"],"post_id":x["id"],"score":x.get("score"),"comments":x.get("descendants"),"published_unix":x.get("time"),"source_url":"https://news.ycombinator.com/item?id="+str(x["id"])} for x in rows if x and not x.get("deleted")]
def reddit(sub):
    url=f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
    return [{"post_id":x["data"]["id"],"score":x["data"].get("score"),"comments":x["data"].get("num_comments"),"published_unix":x["data"].get("created_utc"),"source_url":"https://www.reddit.com"+x["data"]["permalink"]} for x in j(url)["data"]["children"] if not x["data"].get("stickied")]
def harmony():
    url="https://fangzhou.club/"
    p=Ark();p.feed(get(url))
    rows=[{"name":title.strip(),"source_url":"https://fangzhou.club"+href,"signal":"directory link, not rank"} for href,title in p.links if title.strip()]
    if not rows:raise ValueError("No identifiable application links")
    return list({x["source_url"]:x for x in rows}.values())
def android():
    from google_play_scraper import collection
    # Unsupported library versions must fail explicitly rather than invent rankings.
    rows=collection(collection="TOP_FREE",category="APPLICATION",lang="en",country="us",results=50)
    return [{"name":x["title"],"product_id":"android:"+x["appId"],"store_url":"https://play.google.com/store/apps/details?id="+x["appId"],"source_url":"https://play.google.com/store/apps/top","signal":"collection order; rank not asserted"} for x in rows]
def main():
    tasks={**{f"apple_{r}_{k}":lambda r=r,k=k:apple(r,k) for r in ("us","cn") for k in ("apps","games")},"hf_models":lambda:hf("models"),"hf_spaces":lambda:hf("spaces"),"hackernews":hn,"harmony":harmony,"android":android,**{f"reddit_{s}":lambda s=s:reddit(s) for s in ("iosapps","androidapps","SideProject","IndieDev")}}
    result={"date":DAY,"observed_at":NOW,"status":"unreviewed_observations","sources":{}}
    for name,fn in tasks.items():
        try:
            rows=fn()
            result["sources"][name]={"status":"ok" if rows else "empty","records":rows}
        except Exception as e:
            result["sources"][name]={"status":"unavailable","reason":type(e).__name__}
        print(name,result["sources"][name]["status"])
    dest=ROOT/"snapshots"/DAY/(NOW[11:19].replace(":","")+"Z.json")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    if not any(s["status"]=="ok" for s in result["sources"].values()):raise SystemExit("All sources failed")
if __name__=="__main__":main()
