#!/usr/bin/env python3
"""EduTech期刊追踪 - OpenAlex数据抓取脚本（合并优化版）"""

import json
import os
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path

# 配置
OPENALEX_BASE_URL = "https://api.openalex.org"
EMAIL = os.environ.get("OPENALEX_EMAIL", "")
DAYS_BACK = 7
MAX_KEEP_DAYS = 90  # 只保留最近90天的文章


def load_journals():
    """加载期刊配置"""
    config_path = Path(__file__).parent.parent / 'config' / 'journals.json'
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_existing_articles():
    """加载已有文章数据"""
    data_path = Path(__file__).parent.parent / 'public' / 'data' / 'articles.json'
    if data_path.exists():
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return []
    return []


def save_articles(articles):
    """保存文章数据"""
    data_path = Path(__file__).parent.parent / 'public' / 'data' / 'articles.json'
    data_path.parent.mkdir(parents=True, exist_ok=True)
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)


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


def fetch_works_by_issn(issn, from_date, to_date):
    """通过ISSN从OpenAlex获取论文"""
    params = {
        "filter": f"primary_location.source.issn:{issn},from_publication_date:{from_date},to_publication_date:{to_date}",
        "sort": "publication_date:desc",
        "per_page": 50,
    }
    if EMAIL:
        params["mailto"] = EMAIL

    try:
        response = requests.get(
            f"{OPENALEX_BASE_URL}/works",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("results", [])
    except requests.exceptions.RequestException as e:
        print(f"  ⚠️ 请求失败 (ISSN: {issn}): {e}")
        return []


def extract_article_info(work, journal_name, journal_jif):
    """从OpenAlex work对象提取文章信息"""
    # 作者
    authors = []
    for authorship in work.get("authorships", [])[:5]:
        author = authorship.get("author", {})
        name = author.get("display_name", "Unknown")
        authors.append(name)

    # DOI
    doi = work.get("doi", "") or ""
    if doi.startswith("https://doi.org/"):
        doi = doi[16:]

    # 关键词
    keywords = []
    for kw in work.get("keywords", [])[:5]:
        keywords.append(kw.get("display_name", ""))
    if not keywords:
        for concept in work.get("concepts", [])[:5]:
            if concept.get("score", 0) > 0.3:
                keywords.append(concept.get("display_name", ""))

    # 摘要
    abstract = reconstruct_abstract(work.get("abstract_inverted_index"))

    # Open Access
    oa_info = work.get("open_access", {})
    is_oa = oa_info.get("is_oa", False)
    oa_url = oa_info.get("oa_url", "")

    return {
        "id": work.get("id", ""),
        "title": work.get("title", "No Title"),
        "authors": authors,
        "journal": journal_name,
        "jif": journal_jif,
        "published_date": work.get("publication_date", ""),
        "doi": doi,
        "url": work.get("primary_location", {}).get("landing_page_url", "") or work.get("doi", ""),
        "abstract": abstract[:500] if abstract else "",
        "keywords": keywords,
        "open_access": is_oa,
        "oa_url": oa_url,
        "cited_by_count": work.get("cited_by_count", 0),
        "type": work.get("type", ""),
        "fetched_at": datetime.now().isoformat()
    }


def generate_summary(new_articles, all_articles, from_date, to_date):
    """生成邮件摘要"""
    lines = []
    lines.append(f"📅 运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"📊 本次新增文章：{len(new_articles)} 篇")
    lines.append(f"📚 数据库总文章数：{len(all_articles)} 篇")
    lines.append(f"🔍 查询范围：{from_date} 至 {to_date}")
    lines.append("")

    if new_articles:
        # 按期刊分组统计
        journal_counts = {}
        for a in new_articles:
            j = a.get("journal", "未知")
            journal_counts[j] = journal_counts.get(j, 0) + 1

        lines.append("📊 各期刊新增统计：")
        lines.append("-" * 40)
        for j_name, count in sorted(journal_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  • {j_name}: {count} 篇")
        lines.append("")

        lines.append("=" * 50)
        lines.append("📝 新增文章详情：")
        lines.append("=" * 50)
        for i, article in enumerate(new_articles[:50], 1):
            lines.append(f"")
            lines.append(f"[{i}] {article.get('title', '无标题')}")
            lines.append(f"    期刊：{article.get('journal', '未知')} (JIF: {article.get('jif', 'N/A')})")
            authors = article.get('authors', [])
            if authors:
                author_str = ', '.join(authors[:3])
                if len(authors) > 3:
                    author_str += f" 等({len(authors)}人)"
                lines.append(f"    作者：{author_str}")
            lines.append(f"    日期：{article.get('published_date', '未知')}")
            if article.get('keywords'):
                lines.append(f"    关键词：{', '.join(article['keywords'][:5])}")
            if article.get('doi'):
                lines.append(f"    DOI：https://doi.org/{article['doi']}")
            if article.get('open_access'):
                lines.append(f"    🔓 开放获取")

        if len(new_articles) > 50:
            lines.append(f"\n... 还有 {len(new_articles) - 50} 篇未显示")
    else:
        lines.append("本次运行没有发现新文章。")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("EduTech 期刊追踪 - 数据抓取")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 日期范围
    today = datetime.now()
    from_date = (today - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")
    print(f"查询范围: {from_date} 至 {to_date}\n")

    # 加载期刊列表
    journals = load_journals()
    print(f"共 {len(journals)} 本期刊待查询\n")

    # 加载已有文章
    existing_articles = load_existing_articles()
    existing_ids = {a.get("id") for a in existing_articles}

    # 抓取新文章
    new_articles = []
    for i, journal in enumerate(journals, 1):
        issn = journal.get("issn", "")
        name = journal.get("name", "未知期刊")
        jif = journal.get("jif", 0)
        print(f"[{i}/{len(journals)}] {name} (JIF: {jif})", end=" ... ")

        works = fetch_works_by_issn(issn, from_date, to_date)
        count = 0
        for work in works:
            article = extract_article_info(work, name, jif)
            if article["id"] and article["id"] not in existing_ids:
                new_articles.append(article)
                existing_ids.add(article["id"])
                count += 1

        if count > 0:
            print(f"✅ {len(works)} 篇中新增 {count} 篇")
        else:
            print(f"无新文章 (共 {len(works)} 篇)")

        time.sleep(0.5)

    # 合并文章
    all_articles = new_articles + existing_articles

    # 按发表日期排序（最新在前）
    all_articles.sort(key=lambda x: x.get("published_date", ""), reverse=True)

    # 清理90天以前的旧文章
    cutoff_date = (today - timedelta(days=MAX_KEEP_DAYS)).strftime("%Y-%m-%d")
    all_articles = [a for a in all_articles if a.get("published_date", "") >= cutoff_date]

    # 保存
    save_articles(all_articles)

    print(f"\n{'=' * 60}")
    print(f"✅ 完成！新增 {len(new_articles)} 篇，总计 {len(all_articles)} 篇")
    print(f"{'=' * 60}")

    # 生成邮件摘要
    summary_text = generate_summary(new_articles, all_articles, from_date, to_date)
    summary_path = Path(__file__).parent.parent / 'public' / 'data' / 'summary.txt'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary_text)

    print("\n📧 邮件摘要已生成")
    print(summary_text)


if __name__ == "__main__":
    main()
