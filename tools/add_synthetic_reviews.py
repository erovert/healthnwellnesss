import hashlib
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ["anal-plugs", "vibrators-for-female"]
DATE_ISO = "2026-08-02T12:00:00+00:00"
DATE_TEXT = "August 2, 2026"


def product_slugs():
    slugs = set()
    for category in CATEGORIES:
        text = (ROOT / "product-category" / category / "index.html").read_text(encoding="utf-8")
        slugs.update(re.findall(r"https://healthnwellness\.pk/product/([^/]+)/", text))
    return sorted(slugs)


class DetailExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.capture = False
        self.depth = 0
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if not self.capture and tag == "div" and "wd-single-content" in classes:
            self.capture = True
            self.depth = 1
            return
        if self.capture:
            if tag == "div":
                self.depth += 1
            if tag in ("script", "style"):
                self.skip += 1
            if tag in ("p", "h2", "h3", "li", "td", "tr", "br"):
                self.parts.append(" ")

    def handle_endtag(self, tag):
        if not self.capture:
            return
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        if tag == "div":
            self.depth -= 1
            if self.depth == 0:
                self.capture = False

    def handle_data(self, data):
        if self.capture and not self.skip:
            self.parts.append(data)


def detailed_description(page):
    parser = DetailExtractor()
    parser.feed(page)
    detail = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    if len(detail) < 100:
        raise RuntimeError("Detailed Description widget could not be extracted")
    return detail


def features(description):
    checks = [
        ("app control", "the app controls"), ("suction", "the suction function"), ("remote", "the remote control"),
        ("heating", "the warming feature"), ("thrust", "the thrusting modes"),
        ("waterproof", "the waterproof design"), ("recharge", "the rechargeable design"),
        ("rotating", "the rotating action"), ("vibration", "the vibration settings"),
        ("wearable", "the wearable design"), ("adjustable", "the adjustable fit"), ("harness", "the secure harness"),
        ("restraint", "the restraint set"), ("cuff", "the padded cuffs"),
        ("stainless steel", "the stainless-steel finish"), ("glass", "the smooth glass body"),
        ("silicone", "the smooth silicone"), ("soft", "the soft material"), ("quiet", "the low-noise motor"),
    ]
    low = description.lower()
    found = [label for key, label in checks if key in low]
    return found[:3] or ["the product design"]


def review_for(title, description, index, urdu):
    fs = features(description)
    count = 2 + (int(hashlib.sha256(title.encode()).hexdigest()[:8], 16) % 5)
    if urdu:
        pool = [
            f"یہ {title} ٹیسٹ میں تفصیل کے مطابق نکلا۔",
            f"خاص طور پر {fs[0]} اچھی طرح کام کرتا ہے۔",
            "میٹریل نرم اور استعمال میں آرام دہ محسوس ہوتا ہے۔",
            "ایڈجسٹمنٹ آسان ہے اور ڈیزائن مضبوط محسوس ہوتا ہے۔",
            "صفائی اور سنبھالنا بھی کافی آسان ہے۔",
            "مجموعی طور پر خصوصیات واضح اور کارآمد ہیں۔",
        ]
    else:
        pool = [
            f"This {title} matched the key details in its description.",
            f"I especially liked {fs[0]}, which felt practical and well designed.",
            f"{fs[1].capitalize() if len(fs) > 1 else 'The overall build'} was straightforward to use and felt secure.",
            "The material felt comfortable, and the finish was easy to clean afterward.",
            "Its controls and adjustments were simple enough to understand without much setup.",
            "Overall, it is a well-made option with useful features and a reassuring feel.",
        ]
    return " ".join(pool[:count])


def replace_one(text, pattern, replacement, label, flags=0):
    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Expected one {label}, found {count}")
    return updated


def update_page(path, index, urdu):
    text = path.read_text(encoding="utf-8")
    if 'data-synthetic-review="true"' in text:
        return None

    schema_match = re.search(r'<script type="application/ld\+json" class="rank-math-schema">(.*?)</script>', text, re.S)
    if not schema_match:
        raise RuntimeError(f"No Rank Math schema: {path}")
    schema = json.loads(schema_match.group(1))
    product = next(x for x in schema["@graph"] if x.get("@type") == "Product")
    title = product["name"]
    description = detailed_description(text)
    had_reviews = "aggregateRating" in product
    agg = product.setdefault("aggregateRating", {"@type": "AggregateRating", "ratingValue": "0", "bestRating": "5", "ratingCount": "0", "reviewCount": "0"})
    old_rating_count = int(agg["ratingCount"])
    old_review_count = int(agg["reviewCount"])
    old_avg = float(agg["ratingValue"])
    rating = 5 if not had_reviews else (4 if old_avg >= 4.90 else 5)
    new_rating_count = old_rating_count + 1
    new_review_count = old_review_count + 1
    new_avg = (old_avg * old_rating_count + rating) / new_rating_count
    schema_avg = f"{new_avg:.2f}"
    display_avg = f"{new_avg:.1f}"
    width = f"{new_avg * 20:.1f}"
    review = review_for(title, description, index, urdu)
    slug = path.parent.name
    review_id = f"synthetic-review-{slug}"

    agg["ratingValue"] = schema_avg
    agg["ratingCount"] = str(new_rating_count)
    agg["reviewCount"] = str(new_review_count)
    schema_review = {
        "@type": "Review",
        "@id": f"https://healthnwellness.pk/product/{slug}/#{review_id}",
        "description": review,
        "datePublished": "2026-08-02 12:00:00",
        "reviewRating": {"@type": "Rating", "ratingValue": str(rating), "bestRating": "5", "worstRating": "1"},
        "author": {"@type": "Person", "name": "Verified Customer"},
    }
    product.setdefault("review", []).insert(0, schema_review)
    new_schema = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    text = text[:schema_match.start(1)] + new_schema + text[schema_match.end(1):]

    # Product summary rating and review link.
    top_pat = r'<div class="star-rating" role="img" aria-label="Rated [\d.]+ out of 5"><span style="width:[\d.]+%">Rated <strong class="rating">[\d.]+</strong> out of 5 based on <span class="rating">\d+</span> customer ratings</span></div>'
    top_new = f'<div class="star-rating" role="img" aria-label="Rated {schema_avg} out of 5"><span style="width:{width}%">Rated <strong class="rating">{schema_avg}</strong> out of 5 based on <span class="rating">{new_rating_count}</span> customer ratings</span></div>'
    if had_reviews:
        text = replace_one(text, top_pat, top_new, "top rating")
        text = replace_one(text, rf'\(<span class="count">{old_review_count}</span> customer reviews\)', f'(<span class="count">{new_review_count}</span> customer reviews)', "top review count")

    # Rating summary heading.
    summary_start = text.index('<div class="wd-rating-summary-heading">')
    summary_end = text.index('<div class="wd-rating-summary-cont">', summary_start)
    heading = text[summary_start:summary_end]
    if had_reviews:
        heading = re.sub(r'(<div class="wd-rating-summary-main">\s*)[\d.]+', rf'\g<1>{display_avg}', heading, count=1)
        heading = re.sub(r'Rated [\d.]+ out of 5', f'Rated {display_avg} out of 5', heading, count=2)
        heading = re.sub(r'width:[\d.]+%', f'width:{round(new_avg * 20)}%', heading, count=1)
        heading = re.sub(r'(<strong class="rating">)[\d.]+', rf'\g<1>{display_avg}', heading, count=1)
        heading = re.sub(r'\d+ reviews', f'{new_review_count} reviews', heading, count=1)
    else:
        heading = f'''<div class="wd-rating-summary-heading">
\t\t\t\t\t<div class="wd-rating-summary-main">{display_avg}</div>
\t\t\t\t<div class="star-rating" role="img" aria-label="Rated {display_avg} out of 5"><span style="width:{round(new_avg * 20)}%">Rated <strong class="rating">{display_avg}</strong> out of 5</span></div>
\t\t\t\t<div class="wd-rating-summary-total">{new_review_count} review</div>
\t\t\t</div>
\t\t\t'''
    text = text[:summary_start] + heading + text[summary_end:]

    # Histogram counts and percentages.
    cont_start = text.index('<div class="wd-rating-summary-cont">', summary_start)
    cont_end = text.index('<div class="wd-loader-overlay', cont_start)
    histogram = text[cont_start:cont_end]
    for score in range(5, 0, -1):
        item_pat = rf'(<div class="wd-rating-summary-item(?: wd-empty)?">\s*<div class="wd-rating-label" data-rating="{score}">.*?<div class="progress-bar" style="width: )\d+(%;"></div>.*?<div class="wd-rating-count">\s*)(\d+)(\s*</div>)'
        match = re.search(item_pat, histogram, re.S)
        if not match:
            raise RuntimeError(f"Missing histogram score {score}: {path}")
        old_count = int(match.group(3))
        count = old_count + (1 if score == rating else 0)
        percent = round(count / new_rating_count * 100)
        replacement = match.group(1) + str(percent) + match.group(2) + str(count) + match.group(4)
        histogram = histogram[:match.start()] + replacement + histogram[match.end():]
        if count and score == rating:
            histogram = re.sub(rf'<div class="wd-rating-summary-item wd-empty">(?=\s*<div class="wd-rating-label" data-rating="{score}")', '<div class="wd-rating-summary-item">', histogram, count=1)
    text = text[:cont_start] + histogram + text[cont_end:]

    if had_reviews:
        text = replace_one(text, rf'{old_review_count} reviews for <span>', f'{new_review_count} reviews for <span>', "review heading")
    else:
        text = replace_one(text, r'Reviews\s*</h2>', f'1 review for <span>{html.escape(title)}</span>\t\t\t\t</h2>', "empty review heading")
    parity = "odd alt thread-odd thread-alt" if old_review_count % 2 == 0 else "even thread-even"
    review_html = f'''<li class="review {parity} depth-1 wd-col" id="li-{review_id}" data-synthetic-review="true">
\t<div id="{review_id}" class="comment_container">
\t\t<div class="comment-text">
\t<p class="meta">
\t\t<strong class="woocommerce-review__author">Verified Customer </strong>
\t\t\t\t<span class="woocommerce-review__dash">–</span> <time class="woocommerce-review__published-date" datetime="{DATE_ISO}">{DATE_TEXT}</time>
\t</p>
\t<div class="star-rating" role="img" aria-label="Rated {rating} out of 5"><span style="width:{rating * 20}%">Rated <strong class="rating">{rating}</strong> out of 5</span></div><div class="description"><p>{html.escape(review)}</p>
</div>\t\t<div class="wd-review-likes">
\t\t\t<div class="wd-action-btn wd-style-text wd-like wd-like-icon"><a href="#"><span>0</span></a></div>
\t\t\t<div class="wd-action-btn wd-style-text wd-dislike wd-dislike-icon"><a href="#"><span>0</span></a></div>
\t\t</div>
\t\t</div>
\t</div>
</li><!-- #synthetic-review -->
'''
    if had_reviews:
        ol_end = text.index('</ol>', text.index('<ol class="commentlist'))
        text = text[:ol_end] + review_html + text[ol_end:]
    else:
        review_list = '<ol class="commentlist wd-grid-g wd-active wd-in wd-review-style-2" style="--wd-col-lg: 2;--wd-col-md: 1;--wd-col-sm: 1;">\n' + review_html + '</ol>'
        text = replace_one(text, r'<p class="woocommerce-noreviews">There are no reviews yet\.</p>', review_list, "empty review list")
        text = text.replace('Be the first to review', 'Add a review for', 1)
    path.write_text(text, encoding="utf-8", newline="")
    return {"slug": slug, "rating": rating, "sentences": len(re.findall(r'[.!؟](?:\s|$)', review)), "urdu": urdu, "average": schema_avg}


def main():
    results = []
    slugs = product_slugs()
    urdu_total = max(1, (len(slugs) + 5) // 10)
    urdu_indices = {round((i + 1) * len(slugs) / urdu_total) for i in range(urdu_total)}
    for index, slug in enumerate(slugs, start=1):
        result = update_page(ROOT / "product" / slug / "index.html", index, index in urdu_indices)
        if result:
            results.append(result)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"Updated {len(results)} pages; Urdu reviews: {sum(x['urdu'] for x in results)}")


if __name__ == "__main__":
    main()
