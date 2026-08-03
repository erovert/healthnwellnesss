import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []
pages = 0
for path in sorted((ROOT / "product").glob("*/index.html")):
    text = path.read_text(encoding="utf-8")
    if "synthetic-review-" in text or "data-synthetic-review" in text:
        errors.append(f"{path.parent.name}: added-review marker remains")
    match = re.search(r'<script type="application/ld\+json" class="rank-math-schema">(.*?)</script>', text, re.S)
    if not match:
        continue
    schema = json.loads(match.group(1))
    products = [x for x in schema.get("@graph", []) if x.get("@type") == "Product"]
    if not products:
        continue
    pages += 1
    product = products[0]
    agg = product.get("aggregateRating")
    visible = len(re.findall(r'<li class="review ', text))
    schema_reviews = len(product.get("review", []))
    if agg:
        declared = int(agg["reviewCount"])
        if declared != visible or declared != schema_reviews:
            errors.append(f"{path.parent.name}: counts schema={declared}, visible={visible}, review-array={schema_reviews}")
    elif visible or schema_reviews:
        errors.append(f"{path.parent.name}: reviews remain without aggregate rating")

print(json.dumps({"product_pages_checked": pages, "errors": errors}, indent=2))
raise SystemExit(bool(errors))
