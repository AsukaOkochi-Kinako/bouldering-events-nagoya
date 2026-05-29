import re
import requests
from bs4 import BeautifulSoup
import json
import datetime
import time
from urllib.parse import urljoin, urlparse

# ===========================
#  ジム設定
# ===========================
GYMS = [
    {
        "id": "knot",
        "name": "KNOT",
        "url": "https://www.bouldering-knot.com/",
        "instagram_handle": None,
        "instagram_primary": False,
        "note": None,
        "station": None,  # 自動抽出、または手動で入力
    },
    {
        "id": "pinna",
        "name": "Pinna2",
        "url": "https://pinna2.com/",
        "instagram_handle": None,
        "instagram_primary": True,
        "note": "体験会情報はInstagramで発信",
        "station": None,
    },
    {
        "id": "dbc",
        "name": "D-BC 浅間通",
        "url": "https://www.d-b-c.jp/top/sengen-cho/",
        "instagram_handle": None,
        "instagram_primary": False,
        "note": "試し履き実施状況は要確認",
        "station": "浅間町駅",
    },
    {
        "id": "colorful",
        "name": "Colorful Rock",
        "url": "https://colorfulrock.com/",
        "instagram_handle": None,
        "instagram_primary": False,
        "note": None,
        "station": "東海通駅",
    },
    {
        "id": "cuore",
        "name": "Climbing Cuore",
        "url": "https://climbing-cuore.com/",
        "instagram_handle": None,
        "instagram_primary": False,
        "note": None,
        "station": None,
    },
    {
        "id": "bolsta",
        "name": "Bolsta",
        "url": "https://bolsta.storeinfo.jp/",
        "instagram_handle": None,
        "instagram_primary": False,
        "note": None,
        "station": None,
    },
    {
        "id": "tenova",
        "name": "TENova Climbing",
        "url": "https://tenova-climbing.com/",
        "instagram_handle": None,
        "instagram_primary": False,
        "note": None,
        "station": None,
    },
    {
        "id": "soleil",
        "name": "Climbing Gym Soleil2",
        "url": "https://climbing-gym-soleil2.com/",
        "instagram_handle": None,
        "instagram_primary": False,
        "note": None,
        "station": None,
    },
]

# 体験会関連キーワード
KEYWORDS = [
    "体験会", "試し履き", "無料体験", "初心者体験", "体験イベント",
    "体験レッスン", "はじめての", "初めての", "初心者向け体験",
    "シューズ体験", "クライミング体験",
]

# ニュース・イベントページのパターン
EVENT_PAGE_PATTERNS = [
    "news", "blog", "event", "events", "schedule", "info", "topics",
    "お知らせ", "ニュース", "イベント", "スケジュール", "ブログ",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# 日付パターン（年省略可、曜日・時刻付き可）
DATE_RE = re.compile(
    r'(?:\d{4}年\s*)?'
    r'\d{1,2}月\s*\d{1,2}日'
    r'(?:\s*[（(][月火水木金土日祝][)）])?'
    r'(?:\s*\d{1,2}[:：]\d{2}(?:\s*[〜～~]\s*\d{1,2}[:：]\d{2})?)?'
)
RECURRING_RE = re.compile(r'毎月|毎週|定期|第[一二三四五1-5]\s*[土日月火水木金]曜')

STATION_RE = re.compile(r'([ぁ-んァ-ン一-龯A-Za-z0-9]+駅)')

def extract_station(texts):
    """複数テキストから最寄駅を抽出する"""
    for text in texts:
        # 「最寄駅: 〇〇駅」パターンを優先
        m = re.search(r'最寄[りり]?\s*[：:\s「]\s*([ぁ-んァ-ン一-龯A-Za-z0-9]+駅)', text)
        if m:
            return m.group(1)
        # 「〇〇駅から徒歩」パターン
        m = re.search(r'([ぁ-んァ-ン一-龯A-Za-z0-9]+駅)[^\n]{0,15}徒歩', text)
        if m:
            return m.group(1)
    # どちらもなければ最初に出てくる駅名
    for text in texts:
        m = STATION_RE.search(text)
        if m:
            return m.group(1)
    return None


def fetch(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return BeautifulSoup(r.text, "html.parser"), None
    except Exception as e:
        return None, str(e)


def parse_event(context, keyword):
    """コンテキストテキストから日時・概要を構造化抽出する"""
    date = None
    m = DATE_RE.search(context)
    if m:
        date = m.group(0).strip()
    elif RECURRING_RE.search(context):
        rm = RECURRING_RE.search(context)
        date = context[rm.start() : rm.start() + 20].strip()

    sentences = re.split(r'[。！!？?\n]', context)
    relevant = [s.strip() for s in sentences if keyword in s and len(s.strip()) > 8]
    if not relevant:
        relevant = [s.strip() for s in sentences if len(s.strip()) > 8]
    summary = "　".join(relevant[:2])
    summary = re.sub(r'\s{2,}', ' ', summary).strip()[:160]

    return date, summary


def extract_articles(soup, source_url):
    """キーワードを含む記事のタイトル・日時・概要を抽出する（タイトルで重複除去）"""
    seen_titles = set()
    articles = []

    for tag in soup(["script", "style", "meta", "link", "noscript"]):
        tag.decompose()

    page_title = ""
    t = soup.find("title")
    if t:
        page_title = t.get_text(strip=True)

    # ── HTML構造アプローチ: article要素や記事っぽいdiv/liを探す ──
    containers = soup.find_all("article")
    if not containers:
        containers = soup.find_all(
            ["div", "li", "section"],
            class_=re.compile(r'\b(?:post|entry|article|news|item|blog|topics?)\b', re.I)
        )

    for container in containers:
        text = container.get_text(separator=" ", strip=True)
        found_kw = next((kw for kw in KEYWORDS if kw in text), None)
        if not found_kw:
            continue

        # タイトル: コンテナ内の見出し or リンクテキスト
        heading = container.find(re.compile(r'^h[1-4]$'))
        if heading:
            title = heading.get_text(strip=True)
        else:
            a = container.find("a")
            title = a.get_text(strip=True) if a else page_title

        title = title[:80]
        key = title.lower().strip()
        if not key or key in seen_titles:
            continue
        seen_titles.add(key)

        date, summary = parse_event(text, found_kw)
        articles.append({
            "title": title, "keyword": found_kw,
            "date": date, "summary": summary, "source_url": source_url,
        })
        if len(articles) >= 5:
            return articles

    # ── フォールバック: テキストベースで直前の短い行をタイトルに ──
    if not articles:
        text_full = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text_full.split("\n") if len(l.strip()) > 4]

        for i, line in enumerate(lines):
            found_kw = next((kw for kw in KEYWORDS if kw in line), None)
            if not found_kw:
                continue

            # 直前の短い行をタイトル候補にする
            title = page_title
            for j in range(i - 1, max(i - 12, -1), -1):
                cand = lines[j]
                if 5 < len(cand) <= 60 and found_kw not in cand:
                    title = cand
                    break

            title = title[:80]
            key = title.lower().strip()
            if not key or key in seen_titles:
                continue
            seen_titles.add(key)

            context = " ".join(lines[max(0, i - 1) : i + 5])[:400]
            date, summary = parse_event(context, found_kw)
            articles.append({
                "title": title, "keyword": found_kw,
                "date": date, "summary": summary, "source_url": source_url,
            })
            if len(articles) >= 5:
                break

    return articles


def find_sub_pages(soup, base_url):
    """ニュース・イベント系のサブページURLを探す"""
    base_domain = urlparse(base_url).netloc
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        href_l = href.lower()
        text_l = text.lower()

        if any(p in href_l or p in text_l for p in EVENT_PAGE_PATTERNS):
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            if (
                parsed.netloc == base_domain
                and full_url not in links
                and full_url.rstrip("/") != base_url.rstrip("/")
                and parsed.scheme in ("http", "https")
            ):
                links.append(full_url)

    return links[:6]


def scrape_gym(gym):
    result = {
        "id": gym["id"],
        "name": gym["name"],
        "url": gym["url"],
        "instagram_handle": gym["instagram_handle"],
        "instagram_primary": gym["instagram_primary"],
        "note": gym.get("note"),
        "station": gym.get("station"),  # 設定値を優先、なければ自動抽出
        "status": "not_found",
        "snippets": [],
        "last_checked": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "error": None,
    }

    soup, err = fetch(gym["url"])
    if soup is None:
        result["status"] = "error"
        result["error"] = err
        return result

    all_articles = extract_articles(soup, gym["url"])
    page_texts = [soup.get_text(separator=" ", strip=True)]

    sub_pages = find_sub_pages(soup, gym["url"])
    for sub_url in sub_pages[:3]:
        time.sleep(0.8)
        sub_soup, _ = fetch(sub_url)
        if sub_soup:
            all_articles.extend(extract_articles(sub_soup, sub_url))
            page_texts.append(sub_soup.get_text(separator=" ", strip=True))

    # 駅名が未設定なら自動抽出
    if not result["station"]:
        result["station"] = extract_station(page_texts)

    # タイトルで全ページ横断の重複除去
    seen_titles = set()
    unique = []
    for a in all_articles:
        key = a["title"].lower().strip()
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(a)

    result["snippets"] = unique[:5]
    if result["snippets"]:
        result["status"] = "found"

    return result


def main():
    print("=== Bouldering Events Scraper ===")
    gym_results = []

    for gym in GYMS:
        print(f"  Scraping [{gym['id']}] {gym['name']} ...")
        r = scrape_gym(gym)
        gym_results.append(r)
        status_label = {"found": "✓ 発見", "not_found": "－ なし", "error": "✗ エラー"}.get(r["status"], r["status"])
        print(f"    {status_label}  ({len(r['snippets'])} snippets)")
        time.sleep(1.2)

    data = {
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "gyms": gym_results,
    }

    with open("docs/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    found_count = sum(1 for g in gym_results if g["status"] == "found")
    print(f"\n完了。{found_count}/{len(GYMS)} ジムで情報を発見。→ docs/data.json")


if __name__ == "__main__":
    main()
