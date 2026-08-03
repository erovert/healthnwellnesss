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
gram_owners = {}
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
    lowered = body.lower()
    for banned in ("matched the key details in its description", "i especially liked"):
        if banned in lowered:
            errors.append(f"{slug}: contains banned phrase '{banned}'")
    for sentence in re.split(r"[.!؟۔]+", lowered):
        words = re.findall(r"[\w'-]+", sentence, re.UNICODE)
        for position in range(len(words) - 4):
            gram = " ".join(words[position:position + 5])
            gram_owners.setdefault(gram, set()).add(slug)
    feature_values = features(detail)
    while len(feature_values) < 2:
        feature_values.append(["the easy-clean surface", "the balanced shape"][len(feature_values) - 1])
    expected_feature = re.sub(r"^the\s+", "", feature_values[0].lower())
    if expected_feature not in body.lower():
        errors.append(f"{slug}: review lacks a feature derived from full description")
    second_feature = re.sub(r"^the\s+", "", feature_values[1].lower())
    if second_feature not in body.lower():
        errors.append(f"{slug}: review lacks its second description-derived feature")
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

duplicate_grams = {gram: sorted(owners) for gram, owners in gram_owners.items() if len(owners) > 1}
for gram, owners in list(duplicate_grams.items())[:25]:
    errors.append(f"repeated five-word phrase '{gram}' in {', '.join(owners)}")

print(json.dumps({
    "products": len(slugs),
    "synthetic_reviews": len(sentence_counts),
    "urdu_reviews": urdu,
    "urdu_percent": round(urdu / len(sentence_counts) * 100, 1),
    "sentence_range": [min(sentence_counts), max(sentence_counts)],
    "aggregate_range": [min(ratings), max(ratings)],
    "full_description_length_range": [min(detail_lengths), max(detail_lengths)],
    "repeated_five_word_phrases": len(duplicate_grams),
    "errors": errors,
}, ensure_ascii=True, indent=2))
raise SystemExit(bool(errors))
