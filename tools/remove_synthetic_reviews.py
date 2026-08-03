import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_one(text, pattern, replacement, label, flags=0):
    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Expected one {label}, found {count}")
    return updated


def remove_from_page(path):
    text = path.read_text(encoding="utf-8")
    if 'data-synthetic-review="true"' not in text:
        return False

    schema_match = re.search(r'<script type="application/ld\+json" class="rank-math-schema">(.*?)</script>', text, re.S)
    schema = json.loads(schema_match.group(1))
    product = next(x for x in schema["@graph"] if x.get("@type") == "Product")
    reviews = product.get("review", [])
    added = [r for r in reviews if "#synthetic-review-" in r.get("@id", "")]
    if len(added) != 1:
        raise RuntimeError(f"Expected one added schema review on {path}, found {len(added)}")
    added_rating = int(added[0]["reviewRating"]["ratingValue"])
    agg = product["aggregateRating"]
    new_rating_count = int(agg["ratingCount"])
    new_review_count = int(agg["reviewCount"])
    old_rating_count = new_rating_count - 1
    old_review_count = new_review_count - 1

    # Restore histogram first; it is the most reliable source of the original average.
    summary_start = text.index('<div class="wd-rating-summary-heading">')
    cont_start = text.index('<div class="wd-rating-summary-cont">', summary_start)
    cont_end = text.index('<div class="wd-loader-overlay', cont_start)
    histogram = text[cont_start:cont_end]
    restored_counts = {}
    for score in range(5, 0, -1):
        item_pat = rf'(<div class="wd-rating-summary-item(?: wd-empty)?">\s*<div class="wd-rating-label" data-rating="{score}">.*?<div class="progress-bar" style="width: )\d+(%;"></div>.*?<div class="wd-rating-count">\s*)(\d+)(\s*</div>)'
        match = re.search(item_pat, histogram, re.S)
        if not match:
            raise RuntimeError(f"Missing histogram score {score}: {path}")
        count = int(match.group(3)) - (1 if score == added_rating else 0)
        if count < 0:
            raise RuntimeError(f"Negative restored count for score {score}: {path}")
        restored_counts[score] = count
        percent = round(count / old_rating_count * 100) if old_rating_count else 0
        replacement = match.group(1) + str(percent) + match.group(2) + str(count) + match.group(4)
        histogram = histogram[:match.start()] + replacement + histogram[match.end():]
        item_open = rf'<div class="wd-rating-summary-item(?: wd-empty)?">(?=\s*<div class="wd-rating-label" data-rating="{score}")'
        desired = '<div class="wd-rating-summary-item">' if count else '<div class="wd-rating-summary-item wd-empty">'
        histogram = re.sub(item_open, desired, histogram, count=1)
    text = text[:cont_start] + histogram + text[cont_end:]

    reviews.remove(added[0])
    if reviews:
        product["review"] = reviews
    else:
        product.pop("review", None)

    if old_rating_count:
        old_avg = sum(score * count for score, count in restored_counts.items()) / old_rating_count
        schema_avg = f"{old_avg:.2f}"
        display_avg = f"{old_avg:.1f}"
        width = f"{old_avg * 20:.1f}"
        agg["ratingValue"] = schema_avg
        agg["ratingCount"] = str(old_rating_count)
        agg["reviewCount"] = str(old_review_count)
    else:
        product.pop("aggregateRating", None)
        schema_avg = display_avg = width = None

    new_schema = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    # Re-find after visible edits because offsets changed.
    schema_match = re.search(r'<script type="application/ld\+json" class="rank-math-schema">(.*?)</script>', text, re.S)
    text = text[:schema_match.start(1)] + new_schema + text[schema_match.end(1):]

    if old_rating_count:
        top_pat = r'<div class="star-rating" role="img" aria-label="Rated [\d.]+ out of 5"><span style="width:[\d.]+%">Rated <strong class="rating">[\d.]+</strong> out of 5 based on <span class="rating">\d+</span> customer ratings</span></div>'
        top_new = f'<div class="star-rating" role="img" aria-label="Rated {schema_avg} out of 5"><span style="width:{width}%">Rated <strong class="rating">{schema_avg}</strong> out of 5 based on <span class="rating">{old_rating_count}</span> customer ratings</span></div>'
        text = replace_one(text, top_pat, top_new, "top rating")
        text = replace_one(text, rf'\(<span class="count">{new_review_count}</span> customer reviews\)', f'(<span class="count">{old_review_count}</span> customer reviews)', "top review count")

    # Restore summary heading.
    summary_start = text.index('<div class="wd-rating-summary-heading">')
    summary_end = text.index('<div class="wd-rating-summary-cont">', summary_start)
    heading = text[summary_start:summary_end]
    if old_rating_count:
        heading = re.sub(r'(<div class="wd-rating-summary-main">\s*)[\d.]+', rf'\g<1>{display_avg}', heading, count=1)
        heading = re.sub(r'Rated [\d.]+ out of 5', f'Rated {display_avg} out of 5', heading, count=2)
        heading = re.sub(r'width:[\d.]+%', f'width:{round(old_avg * 20)}%', heading, count=1)
        heading = re.sub(r'(<strong class="rating">)[\d.]+', rf'\g<1>{display_avg}', heading, count=1)
        heading = re.sub(r'\d+ reviews?', f'{old_review_count} review' + ('s' if old_review_count != 1 else ''), heading, count=1)
    else:
        heading = '''<div class="wd-rating-summary-heading">
\t\t\t\t\t\t\t\t<div class="star-rating" role="img" aria-label="Rated 0 out of 5">
\t\t\t\t\t\t\t<span style="width:0%">
\t\t\tRated <strong class="rating">0</strong> out of 5\t\t</span>
\t\t\t\t\t\t</div>
\t\t\t\t<div class="wd-rating-summary-total">
\t\t\t\t\t0 reviews\t\t\t\t</div>
\t\t\t</div>
\t\t\t'''
    text = text[:summary_start] + heading + text[summary_end:]

    if old_review_count:
        plural = "review" if old_review_count == 1 else "reviews"
        text = replace_one(text, rf'{new_review_count} reviews? for <span>', f'{old_review_count} {plural} for <span>', "review heading")
    else:
        text = replace_one(text, r'1 review for <span>.*?</span>\s*</h2>', 'Reviews\t\t\t\t</h2>', "empty review heading", re.S)

    # Remove only the marked review list item.
    item_pat = r'<li class="review [^"]+" id="li-synthetic-review-[^"]+" data-synthetic-review="true">.*?</li><!-- #synthetic-review -->\s*'
    text = replace_one(text, item_pat, "", "visible added review", re.S)
    if old_review_count == 0:
        empty_ol = r'<ol class="commentlist wd-grid-g wd-active wd-in wd-review-style-2"[^>]*>\s*</ol>'
        text = replace_one(text, empty_ol, '<p class="woocommerce-noreviews">There are no reviews yet.</p>', "empty review list", re.S)
        text = text.replace('Add a review for', 'Be the first to review', 1)

    path.write_text(text, encoding="utf-8", newline="")
    return True


def main():
    changed = 0
    for path in sorted((ROOT / "product").glob("*/index.html")):
        changed += remove_from_page(path)
    print(f"Removed added reviews from {changed} product pages")


if __name__ == "__main__":
    main()
