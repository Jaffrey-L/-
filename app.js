const DATA_ENDPOINT = "./data/news.json";
const SOURCES_ENDPOINT = "./sources.json";

const TEXT = {
  all: "\u5168\u90e8",
  coreCompany: "\u6838\u5fc3AI\u516c\u53f8\u65b0\u95fb",
  creator: "\u6838\u5fc3AI\u535a\u4e3b",
  solo: "AI\u4e2a\u4eba\u516c\u53f8\u5927\u795e",
  practice: "Vibe/Prompt/Agent\u5b9e\u6218",
  countPrefix: "\u5171",
  countSuffix: "\u6761",
  gradeSuffix: "\u7ea7\u4fe1\u6e90",
  importance: "\u91cd\u8981\u5ea6",
  tags: "\u6807\u7b7e",
  source: "\u6765\u6e90",
  readingScore: "\u53ef\u8bfb\u6027",
  keyPoints: "\u8981\u70b9"
};

const fallbackNews = [
  {
    title: "OpenAI launches DeployCo to help businesses build around intelligence",
    summary: "\u6765\u81ea OpenAI \u7684\u6700\u65b0\u52a8\u6001\uff0c\u5efa\u8bae\u6253\u5f00\u539f\u6587\u6838\u9a8c\u7ec6\u8282\u3002",
    date: "2026-05-11",
    sourceName: "OpenAI",
    sourceUrl: "https://openai.com/news/",
    sourceGrade: "A",
    category: TEXT.coreCompany,
    tags: ["OpenAI", "official"],
    importance: 5
  }
];

const categories = [TEXT.all, TEXT.coreCompany, TEXT.creator, TEXT.solo, TEXT.practice];

const categoryFilter = document.getElementById("categoryFilter");
const gradeFilter = document.getElementById("gradeFilter");
const timeFilter = document.getElementById("timeFilter");
const sortFilter = document.getElementById("sortFilter");
const searchInput = document.getElementById("searchInput");
const resetBtn = document.getElementById("resetBtn");
const newsList = document.getElementById("newsList");
const resultCount = document.getElementById("resultCount");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;"
  })[char]);
}

function initCategoryOptions() {
  categoryFilter.innerHTML = "";
  categories.forEach((cat) => {
    const option = document.createElement("option");
    option.value = cat === TEXT.all ? "all" : cat;
    option.textContent = cat;
    categoryFilter.appendChild(option);
  });
}

function renderNews(items) {
  newsList.innerHTML = "";
  resultCount.textContent = `${TEXT.countPrefix} ${items.length} ${TEXT.countSuffix}`;

  if (!items.length) {
    newsList.innerHTML = `<article class="card empty">${TEXT.countPrefix} 0 ${TEXT.countSuffix}</article>`;
    return;
  }

  items.forEach((item) => {
    const tags = Array.isArray(item.tags) ? item.tags : [];
    const safeUrl = String(item.sourceUrl || "#");
    const card = document.createElement("article");
    card.className = "card";
    card.innerHTML = `
      <div class="meta">
        <span class="chip">${escapeHtml(item.category)}</span>
        <span class="chip grade-${escapeHtml(item.sourceGrade)}">${escapeHtml(item.sourceGrade)}${TEXT.gradeSuffix}</span>
        <span class="chip">${TEXT.importance} ${escapeHtml(item.importance || 0)}</span>
        <span class="chip">${TEXT.readingScore} ${escapeHtml(item.readingScore || 0)}</span>
        <span>${escapeHtml(item.date)}</span>
      </div>
      <div class="card-body">
        ${renderVisual(item)}
        <div class="card-copy">
          <h3>${escapeHtml(item.title)}</h3>
          <p>${escapeHtml(item.summary)}</p>
          ${renderKeyPoints(item.keyPoints)}
          <p class="tagline">${TEXT.tags}: ${escapeHtml(tags.join(" / "))}</p>
          <a href="${escapeHtml(safeUrl)}" target="_blank" rel="noreferrer noopener">${TEXT.source}: ${escapeHtml(item.sourceName)}</a>
        </div>
      </div>
    `;
    newsList.appendChild(card);
  });
}

function renderVisual(item) {
  if (item.imageUrl) {
    return `<a class="visual" href="${escapeHtml(item.sourceUrl)}" target="_blank" rel="noreferrer noopener"><img src="${escapeHtml(item.imageUrl)}" alt=""></a>`;
  }
  const initials = String(item.sourceName || "AI").slice(0, 2).toUpperCase();
  return `<a class="visual visual-fallback" href="${escapeHtml(item.sourceUrl || "#")}" target="_blank" rel="noreferrer noopener">${escapeHtml(initials)}</a>`;
}

function renderKeyPoints(points) {
  if (!Array.isArray(points) || !points.length) return "";
  return `<ul class="key-points">${points.slice(0, 3).map((point) => `<li>${escapeHtml(point)}</li>`).join("")}</ul>`;
}

function inSelectedTimeRange(dateValue) {
  if (!timeFilter || timeFilter.value === "all") return true;
  const days = Number(timeFilter.value);
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return false;
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  return date >= cutoff;
}

function getFilteredNews(newsItems) {
  const selectedCategory = categoryFilter.value;
  const selectedGrade = gradeFilter.value;
  const searchValue = searchInput.value.trim().toLowerCase();
  const selectedSort = sortFilter.value;

  const filtered = newsItems.filter((item) => {
    const categoryMatch = selectedCategory === "all" || item.category === selectedCategory;
    const gradeMatch = selectedGrade === "all" || item.sourceGrade === selectedGrade;
    const timeMatch = inSelectedTimeRange(item.date);
    const tags = Array.isArray(item.tags) ? item.tags.join(" ") : "";
    const keyPoints = Array.isArray(item.keyPoints) ? item.keyPoints.join(" ") : "";
    const textBlob = `${item.title} ${item.summary} ${item.sourceName} ${tags} ${keyPoints}`.toLowerCase();
    const searchMatch = !searchValue || textBlob.includes(searchValue);
    return categoryMatch && gradeMatch && timeMatch && searchMatch;
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
  const practice = newsItems.filter((i) => i.category === TEXT.practice).length;

  document.getElementById("kpiTotal").textContent = String(total);
  document.getElementById("kpiEnterprise").textContent = String(enterprise);
  document.getElementById("kpiAGrade").textContent = total ? `${Math.round((aGrade / total) * 100)}%` : "0%";
  document.getElementById("kpiPractice").textContent = String(practice);
}

function bindEvents(newsItems) {
  const render = () => renderNews(getFilteredNews(newsItems));
  [categoryFilter, gradeFilter, timeFilter, sortFilter].forEach((el) => el.addEventListener("change", render));
  searchInput.addEventListener("input", render);
  resetBtn.addEventListener("click", () => {
    categoryFilter.value = "all";
    gradeFilter.value = "all";
    timeFilter.value = "30";
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
    // Source lists are helpful context, but the news feed remains usable without them.
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
