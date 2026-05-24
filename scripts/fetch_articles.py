# scripts/fetch_articles.py
"""
每日从 OpenAlex API 抓取 65 本教育技术期刊的新发表文章
生成 JSON 文件供前端 Dashboard 使用
"""

import requests
import json
import os
from datetime import datetime, timedelta
from time import sleep

# ===== 配置 =====
# 查询过去几天的文章（避免出版商元数据延迟导致遗漏）
LOOKBACK_DAYS = 7
# OpenAlex API 联系邮箱（提高速率限制，填你自己的邮箱）
OPENALEX_EMAIL = os.environ.get("OPENALEX_EMAIL", "your-email@example.com")
# 输出路径
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "public", "data", "articles.json")

def load_journals():
    """加载期刊列表"""
    journals_path = os.path.join(os.path.dirname(__file__), "journals.json")
    with open(journals_path, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_articles_for_journal(issn, journal_name, from_date):
    """
    通过 OpenAlex API 获取某期刊从指定日期起的新文章
    文档: https://docs.openalex.org/api-entities/works/filter-works
    """
    url = "https://api.openalex.org/works"
    params = {
        "filter": f"primary_location.source.issn:{issn},from_publication_date:{from_date}",
        "sort": "publication_date:desc",
        "per_page": 50,
        "mailto": OPENALEX_EMAIL
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] 请求失败 ({journal_name}): {e}")
        return []
    
    articles = []
    for work in data.get("results", []):
        # 提取作者
        authors = []
        for authorship in work.get("authorships", []):
            author_name = authorship.get("author", {}).get("display_name", "")
            if author_name:
                authors.append(author_name)
        
        # 提取摘要（OpenAlex 返回的是 inverted index 格式，需要还原）
        abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
        
        # 提取 DOI
        doi = work.get("doi", "")
        if doi and doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")
        
        article = {
            "title": work.get("title", "Untitled"),
            "authors": authors[:6],  # 最多显示6位作者
            "abstract": abstract,
            "doi": doi,
            "date": work.get("publication_date", ""),
            "open_access": work.get("open_access", {}).get("is_oa", False),
            "cited_by_count": work.get("cited_by_count", 0),
            "openalex_id": work.get("id", "")
        }
        articles.append(article)
    
    return articles

def reconstruct_abstract(inverted_index):
    """
    将 OpenAlex 的 abstract_inverted_index 还原为正常文本
    格式: {"word": [position1, position2, ...], ...}
    """
    if not inverted_index:
        return ""
    
    # 找到最大位置确定数组长度
    max_pos = 0
    for positions in inverted_index.values():
        for pos in positions:
            if pos > max_pos:
                max_pos = pos
    
    # 重建文本
    words = [""] * (max_pos + 1)
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    
    return " ".join(words)

def main():
    print("=" * 60)
    print(f"EduTech 期刊追踪 - 数据抓取")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 计算查询起始日期
    from_date = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"查询范围: {from_date} 至 {today}")
    print()
    
    # 加载期刊列表
    journals = load_journals()
    print(f"共 {len(journals)} 本期刊待查询")
    print("-" * 60)
    
    results = []
    total_articles = 0
    
    for i, journal in enumerate(journals, 1):
        issn = journal["issn"]
        name = journal["name"]
        jif = journal["jif"]
        
        print(f"[{i}/{len(journals)}] {name} (ISSN: {issn})...", end=" ")
        
        if issn == "N/A" or not issn:
            print("跳过（无ISSN）")
            continue
        
        articles = fetch_articles_for_journal(issn, name, from_date)
        print(f"找到 {len(articles)} 篇")
        
        if articles:
            results.append({
                "journal": name,
                "issn": issn,
                "jif": jif,
                "publisher": journal.get("publisher", ""),
                "article_count": len(articles),
                "articles": articles
            })
            total_articles += len(articles)
        
        # 请求间隔，避免触发速率限制
        sleep(0.2)
    
    # 按 JIF 降序排列
    results.sort(key=lambda x: x["jif"], reverse=True)
    
    # 构建输出数据
    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "query_from_date": from_date,
        "query_to_date": today,
        "total_journals": len(journals),
        "journals_with_articles": len(results),
        "total_articles": total_articles,
        "data": results
    }
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    # 写入 JSON
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print()
    print("=" * 60)
    print(f"完成！共获取 {total_articles} 篇文章，来自 {len(results)} 本期刊")
    print(f"数据已保存至: {OUTPUT_PATH}")
    print("=" * 60)

if __name__ == "__main__":
    main()