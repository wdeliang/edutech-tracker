<template>
  <div class="app">
    <!-- Header -->
    <header class="header">
      <h1>📚 EduTech 期刊追踪</h1>
      <p>教育技术领域顶级期刊最新论文自动追踪</p>
      <div class="last-updated" v-if="lastUpdated">
        最后更新：{{ lastUpdated }}
      </div>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p>正在加载数据...</p>
    </div>

    <template v-else>
      <!-- Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon">📝</div>
          <div class="stat-value">{{ weekArticles }}</div>
          <div class="stat-label">本周新增</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📚</div>
          <div class="stat-value">{{ articles.length }}</div>
          <div class="stat-label">总文章数</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📖</div>
          <div class="stat-value">{{ journalCount }}</div>
          <div class="stat-label">覆盖期刊</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">🔓</div>
          <div class="stat-value">{{ oaPercent }}%</div>
          <div class="stat-label">开放获取</div>
        </div>
      </div>

      <!-- Journal Distribution -->
      <div class="journal-section" v-if="journalDistribution.length">
        <h2>📊 期刊分布 (Top 10)</h2>
        <div v-for="item in journalDistribution.slice(0, 10)" :key="item.name" class="journal-bar">
          <div class="journal-bar-name" :title="item.name">{{ item.name }}</div>
          <div class="journal-bar-track">
            <div class="journal-bar-fill" :style="{ width: (item.count / journalDistribution[0].count * 100) + '%' }">
              <span class="journal-bar-count">{{ item.count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Filters -->
      <div class="filters">
        <input
          v-model="searchQuery"
          class="search-input"
          placeholder="🔍 搜索标题、作者、关键词..."
        >
        <select v-model="selectedJournal" class="filter-select">
          <option value="">全部期刊</option>
          <option v-for="j in journalList" :key="j" :value="j">{{ j }}</option>
        </select>
        <select v-model="sortBy" class="filter-select">
          <option value="date_desc">最新发布</option>
          <option value="date_asc">最早发布</option>
          <option value="cited">被引最多</option>
          <option value="jif">影响因子</option>
        </select>
      </div>

      <!-- Articles -->
      <div class="articles-section">
        <div class="articles-header">
          <h2>📄 文章列表</h2>
          <span class="articles-count">共 {{ filteredArticles.length }} 篇</span>
        </div>

        <div v-if="paginatedArticles.length === 0" class="loading">
          <p>没有找到匹配的文章</p>
        </div>

        <div v-for="article in paginatedArticles" :key="article.id" class="article-card">
          <div class="article-title">
            <a v-if="article.doi" :href="'https://doi.org/' + article.doi" target="_blank">
              {{ article.title }}
            </a>
            <a v-else-if="article.url" :href="article.url" target="_blank">
              {{ article.title }}
            </a>
            <span v-else>{{ article.title }}</span>
          </div>
          <div class="article-meta">
            <span><span class="badge badge-journal">{{ article.journal }}</span></span>
            <span v-if="article.jif" class="badge badge-jif">JIF: {{ article.jif }}</span>
            <span>📅 {{ article.published_date }}</span>
            <span v-if="article.cited_by_count">📖 被引 {{ article.cited_by_count }}</span>
            <span v-if="article.open_access" class="badge badge-oa">🔓 OA</span>
          </div>
          <div class="article-authors" v-if="article.authors && article.authors.length">
            👤 {{ article.authors.slice(0, 5).join(', ') }}
            <span v-if="article.authors.length > 5"> 等{{ article.authors.length }}人</span>
          </div>
          <div class="article-keywords" v-if="article.keywords && article.keywords.length">
            🏷️ {{ article.keywords.join(', ') }}
          </div>
        </div>

        <!-- Pagination -->
        <div class="pagination" v-if="totalPages > 1">
          <button class="page-btn" @click="currentPage--" :disabled="currentPage === 1">
            ← 上一页
          </button>
          <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
          <button class="page-btn" @click="currentPage++" :disabled="currentPage === totalPages">
            下一页 →
          </button>
        </div>
      </div>
    </template>

    <!-- Footer -->
    <footer class="footer">
      <p>数据来源：<a href="https://openalex.org" target="_blank">OpenAlex</a> |
         自动更新：每日北京时间 6:00 |
         <a href="https://github.com/wdeliang/edutech-tracker" target="_blank">GitHub</a>
      </p>
    </footer>
  </div>
</template>

<script>
export default {
  data() {
    return {
      articles: [],
      loading: true,
      searchQuery: '',
      selectedJournal: '',
      sortBy: 'date_desc',
      currentPage: 1,
      perPage: 20
    }
  },
  computed: {
    lastUpdated() {
      if (!this.articles.length) return ''
      const dates = this.articles.map(a => a.published_date).filter(Boolean).sort()
      return dates[dates.length - 1] || ''
    },
    weekArticles() {
      const oneWeekAgo = new Date()
      oneWeekAgo.setDate(oneWeekAgo.getDate() - 7)
      return this.articles.filter(a => {
        if (!a.published_date) return false
        return new Date(a.published_date) >= oneWeekAgo
      }).length
    },
    journalCount() {
      return new Set(this.articles.map(a => a.journal)).size
    },
    oaPercent() {
      if (!this.articles.length) return 0
      const oaCount = this.articles.filter(a => a.open_access).length
      return Math.round(oaCount / this.articles.length * 100)
    },
    journalList() {
      const journals = {}
      this.articles.forEach(a => {
        if (a.journal) journals[a.journal] = (journals[a.journal] || 0) + 1
      })
      return Object.keys(journals).sort((a, b) => journals[b] - journals[a])
    },
    journalDistribution() {
      const counts = {}
      this.articles.forEach(a => {
        if (a.journal) counts[a.journal] = (counts[a.journal] || 0) + 1
      })
      return Object.entries(counts)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count)
    },
    filteredArticles() {
      let result = [...this.articles]

      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase()
        result = result.filter(a =>
          (a.title && a.title.toLowerCase().includes(q)) ||
          (a.authors && a.authors.some(author => author.toLowerCase().includes(q))) ||
          (a.journal && a.journal.toLowerCase().includes(q)) ||
          (a.keywords && a.keywords.some(k => k.toLowerCase().includes(q)))
        )
      }

      if (this.selectedJournal) {
        result = result.filter(a => a.journal === this.selectedJournal)
      }

      switch (this.sortBy) {
        case 'date_desc':
          result.sort((a, b) => (b.published_date || '').localeCompare(a.published_date || ''))
          break
        case 'date_asc':
          result.sort((a, b) => (a.published_date || '').localeCompare(b.published_date || ''))
          break
        case 'cited':
          result.sort((a, b) => (b.cited_by_count || 0) - (a.cited_by_count || 0))
          break
        case 'jif':
          result.sort((a, b) => (b.jif || 0) - (a.jif || 0))
          break
      }

      return result
    },
    totalPages() {
      return Math.ceil(this.filteredArticles.length / this.perPage)
    },
    paginatedArticles() {
      const start = (this.currentPage - 1) * this.perPage
      return this.filteredArticles.slice(start, start + this.perPage)
    }
  },
  watch: {
    searchQuery() { this.currentPage = 1 },
    selectedJournal() { this.currentPage = 1 },
    sortBy() { this.currentPage = 1 }
  },
  async mounted() {
    try {
      const base = import.meta.env.BASE_URL
      const response = await fetch(`${base}data/articles.json`)
      if (response.ok) {
        this.articles = await response.json()
      }
    } catch (e) {
      console.error('加载数据失败:', e)
    } finally {
      this.loading = false
    }
  }
}
</script>
