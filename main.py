import arxiv
from google import genai
import os
from datetime import datetime

def run():
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    # 検索クエリをより確実に（半導体エッチング関連）
    search = arxiv.Search(
        query='all:"Neutral Beam Etching" OR all:"Atomic Layer Etching"',
        max_results=3,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    report = f"# 🔬 半導体最新論文レポート ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
    
    papers = list(search.results())
    
    for paper in papers:
        print(f"Analyzing: {paper.title}")
        prompt = f"以下の論文を読み、技術革新のポイントとビジネスへの影響を日本語で3つの箇条書きで解説してください。\n\nTitle: {paper.title}\nAbstract: {paper.summary}"
        
        try:
            # モデル名をフルパス 'models/gemini-1.5-flash' に変更
            response = client.models.generate_content(
                model='models/gemini-1.5-flash', 
                contents=prompt
            )
            report += f"## {paper.title}\n- **URL**: {paper.entry_id}\n- **AI解析**: \n{response.text}\n\n---\n"
        except Exception as e:
            # 具体的なエラー内容をログに残す
            print(f"Gemini API Error: {e}")
            report += f"## {paper.title}\n- **URL**: {paper.entry_id}\n- **エラー**: 解析中に問題が発生しました（{str(e)[:50]}...）\n\n---\n"
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("Update complete.")

if __name__ == "__main__":
    run()
