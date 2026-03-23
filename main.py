import arxiv
from google import genai
import os
from datetime import datetime
import html
from pathlib import Path


def build_index_html(new_papers: list[dict], generated_at: str) -> str:
    # Insert model output as escaped text so it cannot break the generated HTML.
    if not new_papers:
        return f"""<!doctype html>
<html lang="ja">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>半導体最新論文レポート</title>
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <header class="site-header">
      <div class="container">
        <h1 class="title">🔬 半導体最新論文レポート</h1>
        <p class="subtitle">生成日時: {html.escape(generated_at)}</p>
      </div>
    </header>

    <main class="container">
      <section class="empty">
        <h2 class="empty__title">今日は新しい論文がありませんでした</h2>
        <p class="empty__text">次回実行をお待ちください。</p>
      </section>
    </main>

    <footer class="site-footer">
      <div class="container">
        <small>emi-news-agent</small>
      </div>
    </footer>
  </body>
</html>"""

    cards = []
    for p in new_papers:
        title = html.escape(str(p["title"]))
        url = html.escape(str(p["url"]), quote=True)
        summary = html.escape(str(p["summary"]))

        cards.append(
            f"""<article class="card">
  <h2 class="card__title">{title}</h2>
  <a class="card__link" href="{url}" target="_blank" rel="noopener noreferrer">arXivを開く</a>
  <details class="card__details" open>
    <summary class="card__details-summary">AI解析（要約）</summary>
    <div class="card__summary">{summary}</div>
  </details>
</article>"""
        )

    count = len(new_papers)
    cards_html = "\n".join(cards)
    return f"""<!doctype html>
<html lang="ja">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>半導体最新論文レポート</title>
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <header class="site-header">
      <div class="container">
        <h1 class="title">🔬 半導体最新論文レポート</h1>
        <p class="subtitle">生成日時: {html.escape(generated_at)} / 新規: {count}件</p>
      </div>
    </header>

    <main class="container">
      <section class="grid" aria-label="論文一覧">
        {cards_html}
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

    # 2. 論文検索（最新5件を取得）
    search = arxiv.Search(
        query='all:"Atomic Layer Etching" OR all:"Neutral Beam Etching"',
        max_results=5,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    new_papers = []
    
    # 3. 新しい論文の抽出とAI要約
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

    # 4. レポートの更新（新しい論文がある時のみ実行）
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not new_papers:
        print("今日は新しい論文がありませんでした。")
        index_html = build_index_html([], generated_at)
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(index_html)
        return

    index_html = build_index_html(new_papers, generated_at)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(index_html)

    # 5. 新しい履歴を保存
    with open(history_file, "w", encoding="utf-8") as f:
        f.write("\n".join(processed_ids))
        
    print("🎉 index.html と履歴の更新が完了しました！")

if __name__ == "__main__":
    run()
