import arxiv
from google import genai
import os
from datetime import datetime
import html
import re
from urllib import parse, request
import xml.etree.ElementTree as ET
from pathlib import Path


DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
RSS_GOOGLE_URL = (
    "https://news.google.com/rss/search?q="
    + parse.quote("半導体 OR semiconductor OR chip industry when:1d")
    + "&hl=ja&gl=JP&ceid=JP:ja"
)
RSS_FEEDS = [
    {"name": "Google News", "url": RSS_GOOGLE_URL, "max_items": 6},
    {"name": "IEEE Spectrum", "url": "https://spectrum.ieee.org/feeds/feed.rss", "max_items": 6},
]
RSS_NS = {
    "media": "http://search.yahoo.com/mrss/",
}


def get_archive_dates(archive_dir: Path) -> list[str]:
    if not archive_dir.exists():
        return []
    dates: list[str] = []
    for child in archive_dir.iterdir():
        if child.is_dir() and DATE_DIR_RE.match(child.name):
            dates.append(child.name)
    dates.sort(reverse=True)
    return dates


def fetch_rss_entries(source_name: str, feed_url: str, max_items: int) -> list[dict]:
    try:
        req = request.Request(
            feed_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; emi-news-agent/1.0)"},
        )
        with request.urlopen(req, timeout=20) as response:
            body = response.read()
    except Exception as e:
        print(f"RSS取得失敗: {source_name} ({e})")
        return []

    try:
        root = ET.fromstring(body)
    except Exception as e:
        print(f"RSS解析失敗: {source_name} ({e})")
        return []

    entries: list[dict] = []
    for item in root.findall(".//item")[:max_items]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        published = (
            item.findtext("pubDate")
            or item.findtext("{http://purl.org/dc/elements/1.1/}date")
            or ""
        ).strip()

        if not title or not link:
            continue

        image_url = ""
        media_content = item.find("media:content", RSS_NS)
        if media_content is not None and media_content.get("url"):
            image_url = media_content.get("url", "").strip()

        if not image_url:
            media_thumbnail = item.find("media:thumbnail", RSS_NS)
            if media_thumbnail is not None and media_thumbnail.get("url"):
                image_url = media_thumbnail.get("url", "").strip()

        if not image_url:
            enclosure = item.find("enclosure")
            if enclosure is not None and enclosure.get("url"):
                image_url = enclosure.get("url", "").strip()

        if not image_url and description:
            img_match = IMG_SRC_RE.search(description)
            if img_match:
                image_url = img_match.group(1).strip()

        entries.append(
            {
                "title": title,
                "url": link,
                "summary": description if description else "概要なし",
                "source": source_name,
                "published": published,
                "image_url": image_url,
            }
        )

    return entries


def build_paper_card_html(p: dict) -> str:
    title = html.escape(str(p["title"]))
    url_raw = str(p["url"])
    url = html.escape(url_raw, quote=True)
    summary = html.escape(str(p["summary"]))

    return f"""<article class="card">
  <h2 class="card__title">{title}</h2>
  <div class="card__meta">
    <a class="card__link" href="{url}" target="_blank" rel="noopener noreferrer">arXivを開く</a>
    <p class="card__url">
      <span class="card__url-label">URL</span>:
      <a class="card__url-link" href="{url}" target="_blank" rel="noopener noreferrer">{html.escape(url_raw)}</a>
    </p>
  </div>
  <details class="card__details" open>
    <summary class="card__details-summary">AI解析（要約）</summary>
    <div class="card__summary">{summary}</div>
  </details>
</article>"""


def build_news_card_html(n: dict) -> str:
    title = html.escape(str(n["title"]))
    url = html.escape(str(n["url"]), quote=True)
    summary = html.escape(str(n["summary"]))
    source = html.escape(str(n.get("source", "RSS")))
    published = html.escape(str(n.get("published", "")))
    image_url = html.escape(str(n.get("image_url", "")).strip(), quote=True)

    # 画像がある場合とない場合でリッチに切り替え
    image_html = f'<img class="card__thumb" src="{image_url}" alt="" loading="lazy">' if image_url else '<div class="card__thumb-placeholder">No Image</div>'

    return f"""
    <article class="card">
        <div class="card__image-area">{image_html}</div>
        <div class="card__content">
            <span class="badge">{source}</span>
            <h3 class="card__title"><a href="{url}" target="_blank">{title}</a></h3>
            <p class="summary">{summary[:120]}...</p>
            <div class="card__footer">
                <span class="date">{published}</span>
                <a href="{url}" class="read-more" target="_blank">Read More →</a>
            </div>
        </div>
    </article>
    """


def build_two_sections_html(news_items: list[dict], papers: list[dict]) -> str:
    if news_items:
        news_cards_html = "\n".join(build_news_card_html(n) for n in news_items)
        news_section = f"""<section aria-label="業界ニュース">
  <h2 class="section-title">📰 今日の業界ニュース（Google等）</h2>
  <div class="grid">
    {news_cards_html}
  </div>
</section>"""
    else:
        news_section = """<section aria-label="業界ニュース">
  <h2 class="section-title">📰 今日の業界ニュース（Google等）</h2>
  <div class="empty">
    <p class="empty__text">ニュースはまだ取得できていません。</p>
  </div>
</section>"""

    if papers:
        papers_cards_html = "\n".join(build_paper_card_html(p) for p in papers)
        papers_section = f"""<section aria-label="最新論文">
  <h2 class="section-title">🎓 今日の最新論文（arXiv等）</h2>
  <div class="grid">
    {papers_cards_html}
  </div>
</section>"""
    else:
        papers_section = """<section aria-label="最新論文">
  <h2 class="section-title">🎓 今日の最新論文（arXiv等）</h2>
  <div class="empty">
    <p class="empty__text">今日は新しい論文がありませんでした。</p>
  </div>
</section>"""

    return f"""{news_section}

{papers_section}"""


def build_archive_page_html(news_items: list[dict], papers: list[dict], date_str: str, generated_at: str, css_href: str) -> str:
    body_sections = build_two_sections_html(news_items, papers)
    return f"""<!doctype html>
<html lang="ja">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>半導体ニュース＆論文 - {html.escape(date_str)}</title>
    <link rel="stylesheet" href="{css_href}" />
  </head>
  <body>
    <header class="site-header">
      <div class="container">
        <a class="back-link" href="../../index.html">← トップへ</a>
        <h1 class="title">🔬 {html.escape(date_str)} の半導体トピック</h1>
        <p class="subtitle">生成日時: {html.escape(generated_at)} / ニュース: {len(news_items)}件 / 論文: {len(papers)}件</p>
      </div>
    </header>

    <main class="container">
      {body_sections}
    </main>

    <footer class="site-footer">
      <div class="container">
        <small>emi-news-agent</small>
      </div>
    </footer>
  </body>
</html>"""


def build_root_index_html(
    today_news: list[dict],
    today_papers: list[dict],
    generated_at: str,
    archive_dates: list[str],
) -> str:
    two_sections = build_two_sections_html(today_news, today_papers)
    if archive_dates:
        archive_items = "\n".join(
            f"""<a class="archive-item" href="archive/{d}/index.html">{d}</a>"""
            for d in archive_dates
        )
    else:
        archive_items = """<p class="empty__text">アーカイブはまだありません。</p>"""

    return f"""<!doctype html>
<html lang="ja">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>半導体ニュース＆論文レポート</title>
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <header class="site-header">
      <div class="container">
        <h1 class="title">🔬 半導体ニュース＆論文レポート</h1>
        <p class="subtitle">生成日時: {html.escape(generated_at)} / ニュース: {len(today_news)}件 / 論文: {len(today_papers)}件</p>
      </div>
    </header>

    <main class="container">
      {two_sections}

      <section class="archive-section" aria-label="過去の日付">
        <h2 class="section-title">過去のアーカイブ</h2>
        <div class="archive-list">
          {archive_items}
        </div>
      </section>
    </main>

    <footer class="site-footer">
      <div class="container">
        <small>emi-news-agent</small>
      </div>
    </footer>
  </body>
</html>"""

def run():
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    # 1. 履歴ファイルの読み込み（過去に読んだ論文を思い出す）
    history_file = "history.txt"
    history_path = Path(history_file)
    if history_path.exists():
        with open(history_file, "r", encoding="utf-8") as f:
            processed_ids = set(f.read().splitlines())
    else:
        processed_ids = set()

    # 2. ニュース取得（Google/IEEE RSS）
    today_news: list[dict] = []
    for feed in RSS_FEEDS:
        entries = fetch_rss_entries(feed["name"], feed["url"], feed["max_items"])
        today_news.extend(entries)

    # 3. 論文検索（最新5件を取得）
    search = arxiv.Search(
        query='all:"Atomic Layer Etching" OR all:"Neutral Beam Etching"',
        max_results=5,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    new_papers = []
    
    # 4. 新しい論文の抽出とAI要約
    for paper in list(search.results()):
        # すでに履歴（processed_ids）にあるURLならスキップ
        if paper.entry_id in processed_ids:
            print(f"スキップ (要約済み): {paper.title}")
            continue
            
        print(f"新規論文を発見: {paper.title}")
        prompt = f"以下の半導体論文を日本語で専門的に要約して：\n\nTitle: {paper.title}\nAbstract: {paper.summary}"
        summary = ""
        error_msg = ""
        
        # 2026年最新モデルで要約に挑戦
        for model_name in ['gemini-3.0-flash', 'gemini-2.5-flash', 'gemini-3.1-flash']:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response.text:
                    summary = response.text
                    break
            except Exception as e:
                error_msg += f"({model_name}失敗: {e}) "
                
        if not summary:
            summary = f"⚠️要約できませんでした。原因👉 {error_msg}"
        
        # 新しい論文リストと、履歴リストの両方に追加
        new_papers.append({
            "title": paper.title,
            "url": paper.entry_id,
            "summary": summary
        })
        processed_ids.add(paper.entry_id)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    date_str = datetime.now().strftime("%Y-%m-%d")

    archive_dir = Path("archive") / date_str
    archive_dir.mkdir(parents=True, exist_ok=True)

    # 5. ルートのトップページを生成（過去アーカイブへの導線）
    archive_dates = get_archive_dates(Path("archive"))
    index_html = build_root_index_html(today_news, new_papers, generated_at, archive_dates)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(index_html)

    # 6. 日付ごとのページを生成
    archive_index_html = build_archive_page_html(today_news, new_papers, date_str, generated_at, "../../styles.css")
    with open(archive_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(archive_index_html)

    if not new_papers:
        print("今日は新しい論文がありませんでした（アーカイブページは作成済み）。")
        return

    # 7. 新しい履歴を保存
    with open(history_file, "w", encoding="utf-8") as f:
        f.write("\n".join(processed_ids))
        
    print("🎉 ニュース＋論文の index.html / archive と履歴の更新が完了しました！")

if __name__ == "__main__":
    run()
