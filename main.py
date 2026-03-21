import arxiv
from google import genai
import os
from datetime import datetime

def run():
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    search = arxiv.Search(
        query='all:"Atomic Layer Etching" OR all:"Neutral Beam Etching"',
        max_results=3,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    report = f"# 🔬 半導体最新論文レポート ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
    
    for paper in list(search.results()):
        prompt = f"以下の半導体論文を日本語で要約して：\n\nTitle: {paper.title}\nAbstract: {paper.summary}"
        summary = ""
        error_msg = ""
        
        # 確実に存在するモデル名を試す
        for model_name in ['gemini-2.0-flash', 'gemini-1.5-flash']:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response.text:
                    summary = response.text
                    break
            except Exception as e:
                # 失敗した理由を記録しておく
                error_msg += f"({model_name}の失敗理由: {e}) "
                
        # もし全部失敗したら、エラーの理由をそのまま表示する
        if not summary:
            summary = f"⚠️要約できませんでした。原因はこちらです👉 {error_msg}"
            
        report += f"## {paper.title}\n- **URL**: {paper.entry_id}\n- **AI解析**: \n{summary}\n\n---\n"
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(report)

if __name__ == "__main__":
    run()
