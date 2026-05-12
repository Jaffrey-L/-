const fallbackNews = [
  {
    title: "OpenAI launches enterprise workflow updates for agents",
    summary: "Focuses on controllability, audit logs, and tool reliability for enterprise deployment.",
    date: "2026-05-12",
    sourceName: "OpenAI Blog",
    sourceUrl: "https://openai.com/news/",
    sourceGrade: "A",
    category: "核心AI公司新闻",
    tags: ["enterprise", "agent", "product"],
    importance: 5
  },
  {
    title: "Anthropic publishes safety-eval notes for production AI systems",
    summary: "Covers eval coverage, failure taxonomy, and enterprise governance checkpoints.",
    date: "2026-05-11",
    sourceName: "Anthropic News",
    sourceUrl: "https://www.anthropic.com/news",
    sourceGrade: "A",
    category: "核心AI公司新闻",
    tags: ["safety", "enterprise", "eval"],
    importance: 4
  },
  {
    title: "DeepSeek tooling update triggers China enterprise adoption discussion",
    summary: "Developers highlight integration speed and local deployment tradeoffs.",
    date: "2026-05-12",
    sourceName: "行业媒体汇总",
    sourceUrl: "https://example.com/deepseek-update",
    sourceGrade: "C",
    category: "核心AI公司新闻",
    tags: ["china", "enterprise", "model"],
    importance: 3
  },
  {
    title: "Andrej Karpathy shares pragmatic vibe coding workflow",
    summary: "Suggests iterative prompting loop with fast test harness for coding agents.",
    date: "2026-05-12",
    sourceName: "X Thread",
    sourceUrl: "https://x.com/karpathy",
    sourceGrade: "B",
    category: "Vibe/Prompt/Agent实战",
    tags: ["vibecoding", "prompt", "workflow"],
    importance: 5
  },
  {
    title: "Simon Willison compares agent tool-calling patterns",
    summary: "Breaks down reliability tactics for long-running tool loops in production.",
    date: "2026-05-10",
    sourceName: "Blog Post",
    sourceUrl: "https://simonwillison.net/",
    sourceGrade: "B",
    category: "Vibe/Prompt/Agent实战",
    tags: ["agent", "tool-calling", "engineering"],
    importance: 4
  },
  {
    title: "Pieter Levels posts solo-AI SaaS revenue snapshot",
    summary: "Shows traffic-to-revenue conversion and AI feature-driven retention impacts.",
    date: "2026-05-11",
    sourceName: "X Post",
    sourceUrl: "https://x.com/levelsio",
    sourceGrade: "B",
    category: "AI个人公司大神",
    tags: ["solo", "saas", "growth"],
    importance: 4
  },
  {
    title: "宝玉总结企业内 Agent 落地三阶段",
    summary: "从 PoC、流程嵌入到权限治理，给出中文团队可执行模板。",
    date: "2026-05-12",
    sourceName: "公众号",
    sourceUrl: "https://mp.weixin.qq.com/",
    sourceGrade: "B",
    category: "核心AI博主",
    tags: ["enterprise", "agent", "china"],
    importance: 5
  }
];

const categories = ["全部", "核心AI公司新闻", "核心AI博主", "AI个人公司大神", "Vibe/Prompt/Agent实战"];

const DATA_ENDPOINT = "./data/news.json";
const categoryFilter = document.getElementById("categoryFilter");
const gradeFilter = document.getElementById("gradeFilter");
const sortFilter = document.getElementById("sortFilter");
const searchInput = document.getElementById("searchInput");
const resetBtn = document.getElementById("resetBtn");
const newsList = document.getElementById("newsList");
const resultCount = document.getElementById("resultCount");

function initCategoryOptions() {
  categories.forEach((cat) => {
    const option = document.createElement("option");
    option.value = cat === "全部" ? "all" : cat;
    option.textContent = cat;
    categoryFilter.appendChild(option);
  });
}

function renderNews(items) {
  newsList.innerHTML = "";
  resultCount.textContent = `共 ${items.length} 条`;
  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "card";
    card.innerHTML = `
      <div class="meta">
        <span class="chip">${item.category}</span>
        <span class="chip grade-${item.sourceGrade}">${item.sourceGrade}级信源</span>
        <span class="chip">重要度 ${item.importance}</span>
        <span>${item.date}</span>
      </div>
      <h3>${item.title}</h3>
      <p>${item.summary}</p>
      <p>标签：${item.tags.join(" / ")}</p>
      <a href="${item.sourceUrl}" target="_blank" rel="noreferrer noopener">来源：${item.sourceName}</a>
    `;
    newsList.appendChild(card);
  });
}

function getFilteredNews(newsItems) {
  const selectedCategory = categoryFilter.value;
  const selectedGrade = gradeFilter.value;
  const searchValue = searchInput.value.trim().toLowerCase();
  const selectedSort = sortFilter.value;

  let filtered = newsItems.filter((item) => {
    const categoryMatch = selectedCategory === "all" || item.category === selectedCategory;
    const gradeMatch = selectedGrade === "all" || item.sourceGrade === selectedGrade;
    const textBlob = `${item.title} ${item.summary} ${item.tags.join(" ")} ${item.sourceName}`.toLowerCase();
    const searchMatch = !searchValue || textBlob.includes(searchValue);
    return categoryMatch && gradeMatch && searchMatch;
  });

  if (selectedSort === "latest") {
    filtered.sort((a, b) => new Date(b.date) - new Date(a.date));
  } else {
    filtered.sort((a, b) => b.importance - a.importance);
  }

  return filtered;
}

function bindEvents() {
  [categoryFilter, gradeFilter, sortFilter].forEach((el) =>
    el.addEventListener("change", () => renderNews(getFilteredNews()))
  );
  searchInput.addEventListener("input", () => renderNews(getFilteredNews()));
  resetBtn.addEventListener("click", () => {
    categoryFilter.value = "all";
    gradeFilter.value = "all";
    sortFilter.value = "latest";
    searchInput.value = "";
    renderNews(getFilteredNews());
  });
}

async function renderSourcePools() {
  const response = await fetch("./sources.json");
  const sourceData = await response.json();

  const fill = (id, list) => {
    const ul = document.getElementById(id);
    ul.innerHTML = "";
    list.forEach((name) => {
      const li = document.createElement("li");
      li.textContent = name;
      ul.appendChild(li);
    });
  };

  fill("companySources", sourceData.companies);
  fill("creatorSources", sourceData.creators);
  fill("soloSources", sourceData.soloBuilders);
}

async function loadNewsData() {
  try {
    const response = await fetch(DATA_ENDPOINT, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Failed to load ${DATA_ENDPOINT}: ${response.status}`);
    }
    const data = await response.json();
    return Array.isArray(data.items) ? data.items : fallbackNews;
  } catch (_) {
    return fallbackNews;
  }
}

async function init() {
  const newsItems = await loadNewsData();
  initCategoryOptions();
  bindEventsForNews(newsItems);
  renderNews(getFilteredNews(newsItems));
  await renderSourcePools();
}

function bindEventsForNews(newsItems) {
  [categoryFilter, gradeFilter, sortFilter].forEach((el) =>
    el.addEventListener("change", () => renderNews(getFilteredNews(newsItems)))
  );
  searchInput.addEventListener("input", () => renderNews(getFilteredNews(newsItems)));
  resetBtn.addEventListener("click", () => {
    categoryFilter.value = "all";
    gradeFilter.value = "all";
    sortFilter.value = "latest";
    searchInput.value = "";
    renderNews(getFilteredNews(newsItems));
  });
}
init();
