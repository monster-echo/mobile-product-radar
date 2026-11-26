"""Build a public Pages artifact from explicitly approved, quality-gated reports."""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_site"
if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(ROOT / "docs", OUT)
reports = []
for path in sorted((ROOT / "data").glob("*.json")):
    date = path.stem
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        continue
    quality_path = ROOT / "quality" / f"{date}.json"
    report_path = ROOT / "daily" / f"{date}.md"
    if not quality_path.is_file() or not report_path.is_file():
        continue
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        q = json.loads(quality_path.read_text(encoding="utf-8"))
        scores = q["scores"]
        limits = {"accuracy": 30, "coverage": 20, "business": 20, "actionability": 20, "presentation": 10}
        if not all(type(scores[k]) in (int, float) and 0 <= scores[k] <= v for k,v in limits.items()):
            continue
        if q["total"] != sum(scores[k] for k in limits) or q["total"] < 85 or scores["accuracy"] < 27 or scores["coverage"] < 12:
            continue
        gates = q["hard_gates"]
        required = ("no_fabrication", "date_region", "chart_types", "commercial_license", "json_consistency", "missing_data_disclosed")
        if q.get("status") != "published" or q.get("public_approved") is not True or not all(gates.get(k) is True for k in required):
            continue
        if data["date"] != date or q["date"] != date or not isinstance(data["products"], list) or not all(isinstance(p,dict) and isinstance(p.get("name"),str) for p in data["products"]):
            continue
        fields = ("name","product_id","platform","category","region","chart","rank","opportunity_score","core_function","gameplay","heat_evidence","monetization","uncertainty","source_url","source_urls")
        products = [{k:p[k] for k in fields if k in p} for p in data["products"]]
        # The explicit approval must cover the full Markdown report and selected product fields.
        dest = OUT / "reports" / f"{date}.html"
        dest.parent.mkdir(exist_ok=True)
        import html
        body = html.escape(report_path.read_text(encoding="utf-8"))
        dest.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>日报 '+date+'</title><style>body{max-width:850px;margin:32px auto;padding:16px;font:16px/1.8 system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}</style><a href="../">返回雷达首页</a><pre>'+body+'</pre></html>', encoding="utf-8")
        reports.append({"date":date,"products":products,"quality":{"total":q["total"],"scores":scores},"report_url":f"reports/{date}.html"})
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print(f"Skipped invalid archive: {date}")
(OUT / "manifest.json").write_text(json.dumps({"reports":reports},ensure_ascii=False,indent=2),encoding="utf-8")
(OUT / ".nojekyll").touch()
print(f"Built {len(reports)} approved reports")
