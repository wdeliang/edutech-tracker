// src/App.jsx
import React, { useState, useEffect, useMemo } from 'react';

// 图标组件（简化版，避免依赖）
const Icon = ({ type, size = 16 }) => {
  const icons = {
    book: "📚",
    search: "🔍",
    link: "🔗",
    calendar: "📅",
    refresh: "🔄",
    down: "▼",
    right: "▶",
  };
  return <span style={{ fontSize: size }}>{icons[type] || ""}</span>;
};

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedJournals, setExpandedJournals] = useState(new Set());
  const [expandedAbstracts, setExpandedAbstracts] = useState(new Set());

  useEffect(() => {
    fetch("/data/articles.json")
      .then(res => {
        if (!res.ok) throw new Error("数据文件未找到");
        return res.json();
      })
      .then(json => {
        setData(json);
        // 默认展开所有有文章的期刊
        setExpandedJournals(new Set(json.data.map(j => j.journal)));
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const toggleJournal = (journal) => {
    const next = new Set(expandedJournals);
    if (next.has(journal)) next.delete(journal);
    else next.add(journal);
    setExpandedJournals(next);
  };

  const toggleAbstract = (id) => {
    const next = new Set(expandedAbstracts);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setExpandedAbstracts(next);
  };

  const filteredData = useMemo(() => {
    if (!data) return [];
    if (!searchTerm) return data.data;
    const lower = searchTerm.toLowerCase();
    return data.data
      .map(journal => ({
        ...journal,
        articles: journal.articles.filter(a =>
          a.title.toLowerCase().includes(lower) ||
          a.authors.some(auth => auth.toLowerCase().includes(lower)) ||
          (a.abstract && a.abstract.toLowerCase().includes(lower))
        )
      }))
      .filter(j => j.articles.length > 0);
  }, [data, searchTerm]);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <p>加载中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", flexDirection: "column", gap: 16 }}>
        <p>⚠️ {error}</p>
        <p style={{ color: "#666", fontSize: 14 }}>请先运行 Python 脚本生成数据文件</p>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#f8fafc", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
      {/* Header */}
      <header style={{ backgroundColor: "white", borderBottom: "1px solid #e2e8f0", padding: "16px 24px", position: "sticky", top: 0, zIndex: 10 }}>
        <div style={{ maxWidth: 900, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>📚 EduTech 期刊追踪</h1>
            <p style={{ margin: "4px 0 0", fontSize: 13, color: "#64748b" }}>
              教育技术 SSCI Q1 · 最后更新: {data.last_updated}
            </p>
          </div>
          <div style={{ fontSize: 13, color: "#64748b" }}>
            查询范围: {data.query_from_date} ~ {data.query_to_date}
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 900, margin: "0 auto", padding: "24px 16px" }}>
        {/* Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginBottom: 24 }}>
          <div style={{ background: "white", borderRadius: 12, padding: 16, border: "1px solid #e2e8f0" }}>
            <p style={{ margin: 0, fontSize: 13, color: "#64748b" }}>新文章总数</p>
            <p style={{ margin: "4px 0 0", fontSize: 24, fontWeight: 700, color: "#4f46e5" }}>{data.total_articles}</p>
          </div>
          <div style={{ background: "white", borderRadius: 12, padding: 16, border: "1px solid #e2e8f0" }}>
            <p style={{ margin: 0, fontSize: 13, color: "#64748b" }}>有更新的期刊</p>
            <p style={{ margin: "4px 0 0", fontSize: 24, fontWeight: 700, color: "#059669" }}>{data.journals_with_articles}</p>
          </div>
          <div style={{ background: "white", borderRadius: 12, padding: 16, border: "1px solid #e2e8f0" }}>
            <p style={{ margin: 0, fontSize: 13, color: "#64748b" }}>监控期刊总数</p>
            <p style={{ margin: "4px 0 0", fontSize: 24, fontWeight: 700, color: "#374151" }}>{data.total_journals}</p>
          </div>
        </div>

        {/* Search */}
        <div style={{ marginBottom: 20 }}>
          <input
            type="text"
            placeholder="🔍 搜索标题、作者或关键词..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: "100%", padding: "12px 16px", border: "1px solid #d1d5db", borderRadius: 12, fontSize: 14, boxSizing: "border-box", outline: "none" }}
          />
        </div>

        {/* Journal List */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {filteredData.map((journal) => (
            <div key={journal.journal} style={{ background: "white", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
              <button
                onClick={() => toggleJournal(journal.journal)}
                style={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 20px", border: "none", background: "none", cursor: "pointer", textAlign: "left" }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14, color: "#111827" }}>{journal.journal}</div>
                  <div style={{ fontSize: 12, color: "#6b7280", marginTop: 2 }}>ISSN: {journal.issn} · JIF: {journal.jif}</div>
                </div>
                <span style={{ background: "#eef2ff", color: "#4338ca", fontSize: 12, fontWeight: 500, padding: "4px 10px", borderRadius: 99 }}>
                  {journal.articles.length} 篇 {expandedJournals.has(journal.journal) ? "▼" : "▶"}
                </span>
              </button>

              {expandedJournals.has(journal.journal) && (
                <div style={{ borderTop: "1px solid #f1f5f9" }}>
                  {journal.articles.map((article, idx) => {
                    const articleId = `${journal.issn}-${idx}`;
                    return (
                      <div key={idx} style={{ padding: "14px 20px", borderBottom: "1px solid #f8fafc" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                          <h3 style={{ margin: 0, fontSize: 14, fontWeight: 500, lineHeight: 1.5, color: "#111827", flex: 1 }}>
                            {article.title}
                          </h3>
                          {article.doi && (
                            <a
                              href={`https://doi.org/${article.doi}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ color: "#4f46e5", textDecoration: "none", fontSize: 12, whiteSpace: "nowrap" }}
                            >
                              DOI ↗
                            </a>
                          )}
                        </div>
                        <p style={{ margin: "6px 0 0", fontSize: 12, color: "#4b5563" }}>
                          {article.authors.join(", ")}
                          {article.open_access && <span style={{ marginLeft: 8, color: "#059669", fontWeight: 500 }}>🔓 OA</span>}
                        </p>
                        <p style={{ margin: "4px 0 0", fontSize: 11, color: "#9ca3af" }}>
                          发表日期: {article.date}
                        </p>
                        {article.abstract && (
                          <div style={{ marginTop: 8 }}>
                            <button
                              onClick={() => toggleAbstract(articleId)}
                              style={{ border: "none", background: "none", color: "#4f46e5", fontSize: 12, cursor: "pointer", padding: 0, fontWeight: 500 }}
                            >
                              {expandedAbstracts.has(articleId) ? "收起摘要 ▲" : "查看摘要 ▼"}
                            </button>
                            {expandedAbstracts.has(articleId) && (
                              <p style={{ margin: "8px 0 0", fontSize: 12, color: "#4b5563", lineHeight: 1.7, background: "#f8fafc", padding: 12, borderRadius: 8 }}>
                                {article.abstract}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>

        {filteredData.length === 0 && (
          <div style={{ textAlign: "center", padding: 48, color: "#9ca3af" }}>
            <p>没有找到匹配的文章</p>
          </div>
        )}

        {/* Footer */}
        <div style={{ marginTop: 48, textAlign: "center", fontSize: 12, color: "#9ca3af", paddingBottom: 24 }}>
          <p>数据来源: OpenAlex API · 每日北京时间 06:00 自动更新</p>
        </div>
      </main>
    </div>
  );
}