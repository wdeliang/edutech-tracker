# scripts/fetch_openalex.py
"""
EduTech期刊追踪 - OpenAlex数据抓取脚本
通过ISSN从OpenAlex API获取最新论文
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

# 配置
OPENALEX_BASE_URL = "https://api.openalex.org"
EMAIL = os.environ.get("OPENALEX_EMAIL", "")
DAYS_BACK = 7  # 查询最近7天的论文


def load_journals():
    """加载期刊配置"""
    config_path = Path(__file__).parent.parent / 'config' / 'journals.json'
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def fetch_works_by_issn(issn, from_date, to_date, per_page=25):
    """通过ISSN从OpenAlex获取指定期刊的最新论文"""
    params = {
        "filter": f"primary_location.source.issn:{issn},from_publication_date:{from_date},to_publication_date:{to_date}",
        "sort": "publication_date:desc",
        "per_page": per_page,
    }
    if EMAIL:
        params["mailto"] = EMAIL

    headers = {"User-Agent": f"EduTechTracker/1.0 (mailto:{EMAIL})"}

    try:
        response = requests.get(
            f"{OPENALEX_BASE_URL}/works",
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        print(f"  请求失败 (ISSN: {issn}): {e}")
        return []


def extract_article_info(work, journal_name, journal_jif):
    """从OpenAlex work对象中提取需要的文章信息"""
    # 提取作者
    authors = []
    for authorship in work.get("authorships", [])[:5]:  # 最多取5个作者
        author = authorship.get("author", {})
        name = author.get("display_name", "Unknown")
        authors.append(name)

    # 提取DOI
    doi = work.get("doi", "")
    if doi and doi.startswith("https://doi.org/"):
        doi = doi[16:]  # 去掉前缀，保留纯DOI

    # 提取关键词/概念
    keywords = []
    for keyword in work.get("keywords", [])[:5]:
        keywords.append(keyword.get("display_name", ""))

    # 如果没有keywords，尝试从concepts获取
    if not keywords:
        for concept in work.get("concepts", [])[:5]:
            if concept.get("score", 0) > 0.3:
                keywords.append(concept.get("display_name", ""))

    # 提取摘要
    abstract = ""
    abstract_index = work.get("abstract_inverted_index")
    if abstract_index:
        abstract = reconstruct_abstract(abstract_index)

    # 提取Open Access信息
    oa_info = work.get("open_access", {})
    is_oa = oa_info.get("is_oa", False)
    oa_url = oa_info.get("oa_url", "")

    return {
        "id": work.get("id", ""),
        "title": work.get("title", "No Title"),
        "authors": authors,
        "journal": journal_name,
        "jif": journal_jif,
        "publication_date": work.get("publication_date", ""),
        "doi": doi,
        "url": work.get("primary_location", {}).get("landing_page_url", ""),
        "abstract": abstract[:500] if abstract else "",
        "keywords": keywords,
        "is_open_access": is_oa,
        "oa_url": oa_url,
        "cited_by_count": work.get("cited_by_count", 0),
        "type": work.get("type", ""),
        "fetched_at": datetime.now().isoformat()
    }


def reconstruct_abstract(inverted_index):
    """从倒排索引重建摘要文本"""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join([word for _, word in word_positions])


def load_existing_articles():
    """加载已有的文章数据"""
    data_path = Path(__file__).parent.parent / 'public' / 'data' / 'articles.json'
    if data_path.exists():
        with open(data_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def save_articles(articles):
    """保存文章数据"""
    data_path = Path(__file__).parent.parent / 'public' / 'data' / 'articles.json'
    data_path.parent.mkdir(parents=True, exist_ok=True)
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)


def main():
    print("=" * 60)
    print("EduTech 期刊追踪 - 数据抓取")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 计算日期范围
    today = datetime.now()
    from_date = (today - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")
    print(f"查询范围: {from_date} 至 {to_date}\n")

    # 加载期刊列表
    journals = load_journals()
    print(f"共 {len(journals)} 本期刊待查询\n")

    # 加载已有文章
    existing_articles = load_existing_articles()
    existing_ids = {a["id"] for a in existing_articles}

    # 抓取新文章
    new_articles = []

    for i, journal in enumerate(journals, 1):
        issn = journal["issn"]
        name = journal["name"]
        jif = journal.get("jif", 0)
        print(f"[{i}/{len(journals)}] {name} (ISSN: {issn})")

        works = fetch_works_by_issn(issn, from_date, to_date)
        count = 0
        for work in works:
            article = extract_article_info(work, name, jif)
            if article["id"] and article["id"] not in existing_ids:
                new_articles.append(article)
                existing_ids.add(article["id"])
                count += 1

        print(f"  → 获取到 {len(works)} 篇, 新增 {count} 篇")

        # 礼貌性延迟，避免请求过快
        time.sleep(0.5)

    # 合并并保存
    all_articles = new_articles + existing_articles

    # 按发表日期排序（最新的在前）
    all_articles.sort(key=lambda x: x.get("publication_date", ""), reverse=True)

    # 只保留最近90天的文章，避免数据无限增长
    cutoff_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    all_articles = [a for a in all_articles if a.get("publication_date", "") >= cutoff_date]

    save_articles(all_articles)

    print(f"\n{'=' * 60}")
    print(f"抓取完成!")
    print(f"新增文章: {len(new_articles)} 篇")
    print(f"总文章数: {len(all_articles)} 篇")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()