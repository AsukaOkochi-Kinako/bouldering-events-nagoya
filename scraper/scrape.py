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
    },
    {
        "id": "pinna",
        "name": "Pinna2",
        "url": "https://pinna2.com/",
        "instagram_handle": None,  # TODO: Instagramアカウント名を入力
        "instagram_primary": True,
        "note": "体験会情報はInstagramで発信",
    },
    {
        "id": "dbc",
        "name": "D-BC 浅間通",
        "url": "https://www.d-b-c.jp/top/sengen-cho/",
        "instagram_handle": None,
        "instagram_primary": False,
        "note": "試し履き実施状況は要確認",
    },
    {
        "id": "colorful",
        "name": "Colorful Rock",
        "url": "https://colorfulrock.com/",
        "instagram_handle": None,
        "instagram_primary": False,
        "note": None,
    },
    {
        "id": "cuore",
        "name": "Climbing Cuore",
        "url": "https://climbing-cuore.com/",
        "instagram_handle": None,
        "instagram_primary": False,
        "note": None,
    },
    {
        "id": "bolsta",
        "name": "Bolsta",
        "url": "https://bolsta.storeinfo.jp/",
        "instagram_handle": None,
        "instagram_primary": False,
        "note": None,
    },
    {
        "id": "tenova",
        "name": "TENova Climbing",
        "url": "https://tenova-climbing.com/",
        "instagram_handle": None,
        "instagram_primary": False,
        "note": None,
    },
    {
        "id": "soleil",
        "name": "Climbing Gym Soleil2",
        "url": "https://climbing-gym-soleil2.com/",
        "instagram_handle": None,
        "instagram_primary": False,
        "note": None,
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


def fetch(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return BeautifulSoup(r.text, "html.parser"), None
    except Exception as e:
        return None, str(e)


def extract_snippets(soup, source_url):
    """キーワードを含む文脈テキストを抽出する"""
    snippets = []
    seen = set()

    for tag in soup(["script", "style", "meta", "link", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 4]

    for i, line in enumerate(lines):
        for kw in KEYWORDS:
            if kw in line:
                context = " ".join(lines[max(0, i - 1) : i + 4])[:300]
                if context not in seen:
                    seen.add(context)
                    snippets.append({
                        "keyword": kw,
                        "text": context,
                        "source_url": source_url,
                    })
                break
        if len(snippets) >= 6:
            break

    return snippets


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

    all_snippets = extract_snippets(soup, gym["url"])

    sub_pages = find_sub_pages(soup, gym["url"])
    for sub_url in sub_pages[:3]:
        time.sleep(0.8)
        sub_soup, _ = fetch(sub_url)
        if sub_soup:
            all_snippets.extend(extract_snippets(sub_soup, sub_url))

    # 重複除去
    seen_texts = set()
    unique = []
    for s in all_snippets:
        if s["text"] not in seen_texts:
            seen_texts.add(s["text"])
            unique.append(s)

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
