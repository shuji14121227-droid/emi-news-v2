import arxiv
import google.generativeai as genai
import os
from datetime import datetime

# 金庫からキーを取得
api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

def run():
    # 利用可能なモデルを確認して、最適なものを選ぶ
    model_name = 'gemini-1.5-flash' # デフォルト
    try:
        # 確実に動く名前をリストから探す
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        print(f"利用可能なモデル: {available_models}")
        
        # 'models/gemini-1.5-flash' か 'models/gemini-pro' を優先的に選ぶ
        if 'models/gemini-1.5-flash' in available_models:
            model_name = 'models/gemini-1.5-flash'
        elif 'models/gemini-1.5-flash-latest' in available_models:
            model_name = 'models/gemini-1.5-flash-latest'
        else:
            # 見つからなければリストの最初にあるやつを使う
            model_name = available_models[0]
    except Exception as e:
        print(f"モデル確認中にエラー（スキップします）: {e}")

    print(f"使用するモデル: {model_name}")
    model = genai.GenerativeModel(model_name)

    search = arxiv.Search(
        query="Neutral Beam Etching OR Atomic Layer Etching",
        max_results=3,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    report = f"# 🔬 半導体最新論文レポート ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
    
    results = list(search.results())
    if not results:
        report += "本日の新しい論文は見つかりませんでした。\n"
    else:
        for paper in results:
            prompt = f"あなたは半導体技術の専門家です。以下の論文を読み、日本語で解説してください。\n\nTitle: {paper.title}\nAbstract: {paper.summary}"
            try:
                response = model.generate_content(prompt)
                report += f"## {paper.title}\n- **URL**: {paper.entry_id}\n- **AI解析**: \n{response.text}\n\n---\n"
            except:
                report += f"## {paper.title}\n- **URL**: {paper.entry_id}\n- **エラー**: 解析に失敗しました。\n\n---\n"
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("完了しました。")

if __name__ == "__main__":
    run()
