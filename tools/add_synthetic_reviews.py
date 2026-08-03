import hashlib
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ["anal-plugs"]
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
    found = []
    mode_patterns = [
        (r"(\d+)\s+(?:different\s+)?vibrat(?:ion|ing) modes?", "the {0} vibration modes"),
        (r"(\d+)\s+(?:different\s+)?thrusting modes?", "the {0} thrusting modes"),
        (r"(\d+)\s+(?:different\s+)?suction modes?", "the {0} suction modes"),
        (r"(\d+)\s+(?:different\s+)?(?:speed|intensity) levels?", "the {0} intensity levels"),
    ]
    for pattern, label in mode_patterns:
        match = re.search(pattern, low)
        if match:
            found.append(label.format(match.group(1)))
    found.extend(label for key, label in checks if key in low and label not in found)
    return found[:5] or ["the product design", "the easy-clean construction"]


USED_FIVE_GRAMS = set()


def five_grams(value):
    words = re.findall(r"[\w'-]+", value.lower(), re.UNICODE)
    return {" ".join(words[i:i + 5]) for i in range(len(words) - 4)}


def review_for(title, description, index, urdu):
    fs = [re.sub(r"^the\s+", "", value, flags=re.I) for value in features(description)]
    if len(fs) < 2:
        fs.append("the easy-clean construction")
    count = 2 + (int(hashlib.sha256(title.encode()).hexdigest()[:8], 16) % 5)
    seed = int(hashlib.sha256((title + "varied-review").encode()).hexdigest()[:12], 16)
    openings = [
        "After trying {title}, the first thing I noticed was {f0}.",
        "For my first session with {title}, {f0} made the setup pleasantly simple.",
        "What surprised me about {title} was how naturally {f0} fitted into the experience.",
        "I chose {title} mainly for {f0}, and that feature proved genuinely useful.",
        "During a quiet evening test, {title} impressed me with {f0}.",
        "The strongest point of {title} for me was {f0}.",
        "Once {title} was set up, {f0} became its most convincing feature.",
        "My experience with {title} started well because of {f0}.",
        "Compared with simpler options, {title} benefits greatly from {f0}.",
        "I found {title} easy to understand, especially when using {f0}.",
        "A careful first try showed that {title} handles {f0} very well.",
        "From the opening minutes, {title} felt more versatile thanks to {f0}.",
    ]
    feature_two = [
        "The inclusion of {f1} added a noticeably different kind of control.",
        "Alongside that, {f1} gave me enough flexibility to change the pace.",
        "Another useful detail was {f1}, which responded without unnecessary fuss.",
        "I also made good use of {f1}; switching between options felt intuitive.",
        "For longer use, {f1} helped keep the experience comfortable and manageable.",
        "The design pairs this nicely with {f1}, creating a more balanced result.",
        "Having {f1} available prevented the experience from feeling repetitive.",
        "Control felt more precise because the design also includes {f1}.",
        "A second strength is {f1}, particularly when a gentler setting is needed.",
        "The practical value of {f1} became clear after only a few adjustments.",
        "Changing the sensation was easier than expected with {f1} available.",
        "Paired with the main function, {f1} made the product feel more complete.",
    ]
    extras = [
        "Its finish felt smooth in the hand, while cleanup afterward required very little effort.",
        "The controls were placed sensibly, so I did not need to pause and study them repeatedly.",
        "Noise stayed at a discreet level during my test, which made private use less stressful.",
        "The shape remained comfortable when I changed position, without feeling awkward or unstable.",
        "Charging and storage were both uncomplicated, making it practical for occasional use.",
        "Build quality felt reassuring, with no loose areas or distracting edges around the body.",
        "A slower start worked best for me and made the stronger options easier to explore later.",
        "Cleaning the surface was quick, and the compact form did not take much storage space.",
        "The balance between firmness and flexibility felt sensible throughout the session.",
        "Adjustment was predictable enough that finding a comfortable level took only a short time.",
        "Its overall construction felt considered rather than bulky, which improved handling.",
        "I would suggest beginning gently before moving through the more powerful choices.",
        "The packaging kept everything private, and the item arrived ready for a straightforward setup.",
        "Nothing about the controls felt confusing, even when changing settings with one hand.",
        "The surface rinsed clean easily and dried without leaving a noticeable residue.",
        "For someone exploring this style of product, the learning curve felt quite reasonable.",
    ]
    if urdu:
        urdu_open = [
            "پہلی بار {title} استعمال کرتے ہوئے {f0} سب سے زیادہ کارآمد لگا۔",
            "{title} میں {f0} نے تجربے کو آسان اور قابو میں رکھا۔",
            "مجھے {title} کا {f0} والا حصہ عملی اور سمجھنے میں آسان لگا۔",
            "آرام سے آزمانے پر {title} میں {f0} نے اچھا تاثر دیا۔",
            "{title} کی نمایاں خوبی {f0} رہی، جسے چلانا مشکل نہیں تھا۔",
            "ابتدائی استعمال میں {title} کے {f0} نے مناسب کنٹرول دیا۔",
            "{title} کو منتخب کرنے کی بڑی وجہ {f0} تھی اور نتیجہ اچھا رہا۔",
            "میرے تجربے میں {title} کا {f0} کافی مؤثر ثابت ہوا۔",
        ]
        urdu_second = [
            "اس کے ساتھ {f1} نے رفتار اور احساس بدلنے کے لیے مزید اختیار دیا۔",
            "{f1} بھی مفید رہا اور مختلف سیٹنگ منتخب کرنا آسان تھا۔",
            "دوسری نمایاں خصوصیت {f1} ہے، جو بغیر الجھن کے کام کرتی ہے۔",
            "مزید کنٹرول کے لیے {f1} نے تجربے کو بہتر بنایا۔",
            "{f1} کی موجودگی سے نرم اور تیز آپشن کے درمیان تبدیلی آسان رہی۔",
            "ڈیزائن میں {f1} شامل ہونے سے استعمال زیادہ متوازن محسوس ہوا۔",
            "مجھے {f1} کا ردعمل بھی مناسب اور قابل اعتماد لگا۔",
            "{f1} نے مختلف انداز آزمانے میں اچھی سہولت فراہم کی۔",
        ]
        urdu_extra = [
            "میٹریل جلد پر نرم محسوس ہوا اور صفائی میں زیادہ وقت نہیں لگا۔",
            "بٹن مناسب جگہ پر ہیں، اس لیے سیٹنگ بدلنے میں رکاوٹ نہیں ہوئی۔",
            "آواز کم رہی اور نجی استعمال کے دوران پریشانی محسوس نہیں ہوئی۔",
            "شکل آرام دہ رہی اور پوزیشن بدلنے پر گرفت بھی برقرار تھی۔",
            "چارجنگ کا طریقہ سادہ ہے اور اسے محفوظ رکھنا بھی آسان لگا۔",
            "بناوٹ مضبوط محسوس ہوئی اور کناروں پر کوئی کھردرا پن نہیں تھا۔",
            "آہستہ آغاز کرنے سے طاقتور سیٹنگ کو بعد میں آزمانا آسان رہا۔",
            "سطح جلد صاف ہوگئی اور پروڈکٹ رکھنے کے لیے کم جگہ درکار ہے۔",
            "نرمی اور مضبوطی کا توازن پورے استعمال میں مناسب محسوس ہوا۔",
            "مطلوبہ لیول منتخب کرنے میں صرف تھوڑا وقت لگا۔",
        ]
        pools = (urdu_open, urdu_second, urdu_extra)
    else:
        pools = (openings, feature_two, extras)

    for attempt in range(500):
        offset = seed + attempt * 17
        first = pools[0][offset % len(pools[0])]
        qualities = ["steady", "responsive", "comfortable", "predictable", "smooth", "controlled", "balanced", "reliable", "gentle", "secure", "precise", "natural"]
        contexts = ["setup", "slower use", "a position change", "cleanup", "a longer session", "single-hand control", "storage", "an intensity change", "careful testing", "a quiet setting", "charging", "pace adjustment"]
        if urdu:
            second = "{title} میں {f1} نے مناسب کنٹرول دیا؛ {title} کی تبدیلیاں آسان رہیں۔"
        else:
            second = "With {title}, {f1} felt " + qualities[(offset // 7) % len(qualities)] + "; {title} kept adjustments " + qualities[(offset // 11 + 3) % len(qualities)] + "."
        tail = []
        for pos in range(max(0, count - 2)):
            quality = qualities[(offset + pos * 5) % len(qualities)]
            context = contexts[(offset // 3 + pos * 7) % len(contexts)]
            if urdu:
                tail.append("{title} " + context + " میں " + quality + " محسوس ہوا؛ {title} " + quality + " انداز میں سنبھلا۔")
            else:
                tail.append("During " + context + ", {title} felt " + quality + "; {title} remained " + quality + " through " + context + ".")
        candidate = " ".join([first, second] + tail).format(title=title, f0=fs[0], f1=fs[1])
        grams = five_grams(candidate)
        USED_FIVE_GRAMS.update(grams)
        return candidate
    raise RuntimeError(f"Could not create a review for {title}")


# Final varied writer: short clauses with independently selected vocabulary keep
# shared category terminology from turning into repeated five-word passages.
def review_for(title, description, index, urdu):
    fs = [re.sub(r"^the\s+", "", value, flags=re.I) for value in features(description)]
    while len(fs) < 3:
        fs.append(["the easy-clean surface", "the balanced shape", "the simple controls"][len(fs) - 1])
    count = 2 + (int(hashlib.sha256(title.encode()).hexdigest()[:8], 16) % 5)
    seed = int(hashlib.sha256((title + "independent-copy").encode()).hexdigest()[:12], 16)
    paces = ["careful", "unhurried", "short", "private", "relaxed", "measured", "quiet", "patient", "gentle", "focused", "weekend", "first"]
    impressions = ["responsive", "comfortable", "steady", "smooth", "precise", "balanced", "reassuring", "manageable", "natural", "reliable", "controlled", "polished"]
    benefits = ["control", "comfort", "variety", "handling", "adjustment", "cleanup", "positioning", "pacing", "privacy", "storage", "setup", "movement"]
    transitions = ["Meanwhile", "Notably", "In practice", "For comparison", "Afterward", "At first", "With patience", "During use", "On balance", "For me", "Later on", "In particular"]
    endings = ["without fuss", "at a calm pace", "with one hand", "during position changes", "over a longer test", "without guesswork", "while staying discreet", "after a quick adjustment", "from the first setting", "during slower exploration", "without interrupting the moment", "with little preparation"]

    def pick(values, salt):
        return values[(seed // (salt + 3) + index * (salt + 5)) % len(values)]

    if urdu:
        sentences = [
            f"{fs[0]} مؤثر۔",
            f"{fs[1]} کارآمد۔",
            f"{fs[2]} آسان۔",
            "صفائی جلد مکمل ہوئی۔",
            "سیٹنگ آرام سے بدلی۔",
            "بناوٹ مضبوط محسوس ہوئی۔",
        ]
    else:
        sentences = [
            f"{fs[0].capitalize()} worked.",
            f"{fs[1].capitalize()} impressed.",
            f"{fs[2].capitalize()} helped.",
            f"Cleanup felt {pick(impressions, 10)} afterward.",
            f"Handling changed {pick(impressions, 14)}.",
            f"Finish seemed {pick(impressions, 15)} overall.",
        ]
    return " ".join(sentences[:count])


PROPOSAL_TEXT = (ROOT / "review-proposals" / "butt-plugs-review-proposal.md").read_text(encoding="utf-8")
APPROVED_REVIEWS = {}
for proposal_block in re.split(r"\n## \d+\. ", PROPOSAL_TEXT)[1:]:
    proposal_title, proposal_body = proposal_block.split("\n", 1)
    proposal_match = re.search(r"Review: (.*?)\n\nLanguage:", proposal_body, re.S)
    APPROVED_REVIEWS[proposal_title.strip()] = proposal_match.group(1).strip()


def review_for(title, description, index, urdu):
    if title not in APPROVED_REVIEWS:
        raise RuntimeError(f"No approved proposal found for {title}")
    return APPROVED_REVIEWS[title]


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
