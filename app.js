const DATA_ENDPOINT = "./data/news.json";
const SOURCES_ENDPOINT = "./sources.json";

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
  }
];

const categories = ["全部", "核心AI公司新闻", "核心AI博主", "AI个人公司大神", "Vibe/Prompt/Agent实战"];

const categoryFilter = document.getElementById("categoryFilter");
const gradeFilter = document.getElementById("gradeFilter");
const sortFilter = document.getElementById("sortFilter");
const searchInput = document.getElementById("searchInput");
const resetBtn = document.getElementById("resetBtn");
const newsList = document.getElementById("newsList");
const resultCount = document.getElementById("resultCount");

function initCategoryOptions() {
  categoryFilter.innerHTML = "";
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
    const tags = Array.isArray(item.tags) ? item.tags : [];
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
      <p>标签：${tags.join(" / ")}</p>
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

  const filtered = newsItems.filter((item) => {
    const categoryMatch = selectedCategory === "all" || item.category === selectedCategory;
    const gradeMatch = selectedGrade === "all" || item.sourceGrade === selectedGrade;
    const tags = Array.isArray(item.tags) ? item.tags.join(" ") : "";
    const textBlob = `${item.title} ${item.summary} ${item.sourceName} ${tags}`.toLowerCase();
    const searchMatch = !searchValue || textBlob.includes(searchValue);
    return categoryMatch && gradeMatch && searchMatch;
  });

  if (selectedSort === "importance") {
    filtered.sort((a, b) => (b.importance || 0) - (a.importance || 0));
  } else {
    filtered.sort((a, b) => new Date(b.date) - new Date(a.date));
  }
  return filtered;
}

function updateKpis(newsItems) {
  const total = newsItems.length;
  const enterprise = newsItems.filter((i) => (i.tags || []).some((t) => String(t).toLowerCase().includes("enterprise"))).length;
  const aGrade = newsItems.filter((i) => i.sourceGrade === "A").length;
  const practice = newsItems.filter((i) => i.category === "Vibe/Prompt/Agent实战").length;

  document.getElementById("kpiTotal").textContent = String(total);
  document.getElementById("kpiEnterprise").textContent = String(enterprise);
  document.getElementById("kpiAGrade").textContent = total ? `${Math.round((aGrade / total) * 100)}%` : "0%";
  document.getElementById("kpiPractice").textContent = String(practice);
}

function bindEvents(newsItems) {
  const render = () => renderNews(getFilteredNews(newsItems));
  [categoryFilter, gradeFilter, sortFilter].forEach((el) => el.addEventListener("change", render));
  searchInput.addEventListener("input", render);
  resetBtn.addEventListener("click", () => {
    categoryFilter.value = "all";
    gradeFilter.value = "all";
    sortFilter.value = "latest";
    searchInput.value = "";
    render();
  });
}

async function renderSourcePools() {
  try {
    const response = await fetch(SOURCES_ENDPOINT, { cache: "no-store" });
    const sourceData = await response.json();
    const fill = (id, list) => {
      const ul = document.getElementById(id);
      ul.innerHTML = "";
      (list || []).forEach((name) => {
        const li = document.createElement("li");
        li.textContent = name;
        ul.appendChild(li);
      });
    };
    fill("companySources", sourceData.companies);
    fill("creatorSources", sourceData.creators);
    fill("soloSources", sourceData.soloBuilders);
  } catch (_) {
    // keep silent
  }
}

async function loadNewsData() {
  try {
    const response = await fetch(DATA_ENDPOINT, { cache: "no-store" });
    if (!response.ok) throw new Error("load news failed");
    const data = await response.json();
    return Array.isArray(data.items) && data.items.length ? data.items : fallbackNews;
  } catch (_) {
    return fallbackNews;
  }
}

async function init() {
  const newsItems = await loadNewsData();
  initCategoryOptions();
  updateKpis(newsItems);
  bindEvents(newsItems);
  renderNews(getFilteredNews(newsItems));
  await renderSourcePools();
}

init();
