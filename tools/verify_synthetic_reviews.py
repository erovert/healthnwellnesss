import json
import re
from pathlib import Path
from add_synthetic_reviews import detailed_description, features

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ["anal-plugs", "vibrators-for-female"]

slugs = set()
for category in CATEGORIES:
    text = (ROOT / "product-category" / category / "index.html").read_text(encoding="utf-8")
    slugs.update(re.findall(r"https://healthnwellness\.pk/product/([^/]+)/", text))

errors = []
urdu = 0
ratings = []
sentence_counts = []
detail_lengths = []
for slug in sorted(slugs):
    path = ROOT / "product" / slug / "index.html"
    text = path.read_text(encoding="utf-8")
    detail = detailed_description(text)
    detail_lengths.append(len(detail))
    if text.count('data-synthetic-review="true"') != 1:
        errors.append(f"{slug}: visible synthetic review count is not 1")
    match = re.search(r'<script type="application/ld\+json" class="rank-math-schema">(.*?)</script>', text, re.S)
    schema = json.loads(match.group(1))
    product = next(x for x in schema["@graph"] if x.get("@type") == "Product")
    synthetic = [x for x in product.get("review", []) if x.get("@id", "").split("#")[-1].startswith("synthetic-review-")]
    if len(synthetic) != 1:
        errors.append(f"{slug}: schema synthetic review count is not 1")
        continue
    review = synthetic[0]
    rating = int(review["reviewRating"]["ratingValue"])
    ratings.append(float(product["aggregateRating"]["ratingValue"]))
    if rating not in (4, 5):
        errors.append(f"{slug}: review rating {rating}")
    body = review["description"]
    expected_feature = features(detail)[0].lower()
    if expected_feature not in body.lower():
        errors.append(f"{slug}: review lacks a feature derived from full description")
    is_urdu = bool(re.search(r'[\u0600-\u06ff]', body))
    urdu += is_urdu
    count = len(re.findall(r'[.!؟۔](?=\s|$)', body))
    sentence_counts.append(count)
    if not 2 <= count <= 6:
        errors.append(f"{slug}: {count} sentences")
    agg = product["aggregateRating"]
    if int(agg["reviewCount"]) != len(product.get("review", [])):
        errors.append(f"{slug}: schema reviewCount mismatch")
    visible_items = len(re.findall(r'<li class="review ', text))
    if visible_items != int(agg["reviewCount"]):
        errors.append(f"{slug}: visible/schema review count mismatch ({visible_items}/{agg['reviewCount']})")

print(json.dumps({
    "products": len(slugs),
    "synthetic_reviews": len(sentence_counts),
    "urdu_reviews": urdu,
    "urdu_percent": round(urdu / len(sentence_counts) * 100, 1),
    "sentence_range": [min(sentence_counts), max(sentence_counts)],
    "aggregate_range": [min(ratings), max(ratings)],
    "full_description_length_range": [min(detail_lengths), max(detail_lengths)],
    "errors": errors,
}, ensure_ascii=False, indent=2))
raise SystemExit(bool(errors))
