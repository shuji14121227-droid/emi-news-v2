import arxiv
from google import genai
import os
from datetime import datetime

def run():

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")

    client = genai.Client(api_key=api_key)

    search = arxiv.Search(
        query='all:"Atomic Layer Etching" OR all:"Neutral Beam Etching"',
        max_results=3,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    report = f"# 🔬 半導体最新論文レポート ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"

    papers = list(search.results())

    candidates = [
        'gemini-1.5-flash',
        'gemini-2.0-flash'
    ]

    for paper in papers:

        prompt = f"""
以下の半導体論文を日本語で要約してください。

Title:
{paper.title}

Abstract:
{paper.summary}

3行程度で専門的に要約してください。
"""

        summary = "解析失敗"

        for model_id in candidates:

            try:

                print(f"Trying model: {model_id}")

                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt
                )

                print("Response received")

                if hasattr(response,"text") and response.text:
                    summary = response.text
                    break

                else:
                    print("No text in response")

            except Exception as e:

                print("ERROR:",str(e))

        report += f"""## {paper.title}

**URL**
{paper.entry_id}

**AI解析**
{summary}

---

"""

    with open("README.md","w",encoding="utf-8") as f:
        f.write(report)

    print("Success!")


if __name__ == "__main__":
    run()
