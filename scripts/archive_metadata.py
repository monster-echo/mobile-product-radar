import json
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/"_site/manifest.json").read_text())
assert isinstance(m["reports"],list)
now=datetime.now(timezone.utc).isoformat()
records={}
for r in m["reports"]:
    assert r["quality"]["total"]>=85
    for p in r["products"]:
        if not p.get("metadata_id") or not p.get("metadata_observed_at"):continue
        key=(p["metadata_id"],p.get("region") or "unspecified")
        fields=("metadata_id","metadata_observed_at","name","platform","region","developer","icon_url","screenshots","store_url","release_date","live_rating","live_rating_count","live_version","live_updated_at","store_price","detail_source_urls","completeness_score")
        records[key]={k:p[k] for k in fields if k in p}
dest=ROOT/"metadata"/now[:10]/(now[11:19].replace(":","")+"Z.json")
dest.parent.mkdir(parents=True,exist_ok=True)
(ROOT/"snapshots").mkdir(exist_ok=True)
dest.write_text(json.dumps({"observed_at":now,"records":list(records.values())},ensure_ascii=False,indent=2)+"\n")
print("Archived",len(records),"matched metadata records")
