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
  qualityScore: "\u8d28\u91cf\u5206",
  keyPoints: "\u8981\u70b9",
  readMoreNote: "\u5982\u679c\u611f\u5174\u8da3\u8bf7\u70b9\u51fb\u67e5\u770b\u539f\u6587"
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
const TAG_LABELS = {
  official: "\u5b98\u65b9\u52a8\u6001",
  enterprise: "\u4f01\u4e1a\u5e94\u7528",
  creator: "\u535a\u4e3b\u89c2\u70b9",
  practice: "\u5b9e\u6218\u65b9\u6cd5",
  agent: "\u667a\u80fd\u4f53",
  agents: "\u667a\u80fd\u4f53",
  coding: "\u7f16\u7a0b",
  prompt: "\u63d0\u793a\u8bcd",
  workflow: "\u5de5\u4f5c\u6d41",
  research: "\u7814\u7a76",
  model: "\u6a21\u578b",
  search: "\u641c\u7d22",
  video: "\u89c6\u9891",
  newsletter: "\u901a\u8baf",
  "open-source": "\u5f00\u6e90",
  vibecoding: "Vibe Coding"
};

const categoryFilter = document.getElementById("categoryFilter");
const gradeFilter = document.getElementById("gradeFilter");
const sourceFilter = document.getElementById("sourceFilter");
const startDateFilter = document.getElementById("startDateFilter");
const endDateFilter = document.getElementById("endDateFilter");
const presetButtons = Array.from(document.querySelectorAll(".preset-btn"));
const sortFilter = document.getElementById("sortFilter");
const searchInput = document.getElementById("searchInput");
const applyBtn = document.getElementById("applyBtn");
const resetBtn = document.getElementById("resetBtn");
const newsList = document.getElementById("newsList");
const resultCount = document.getElementById("resultCount");
let appliedFilters = null;

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

function initSourceOptions(newsItems) {
  const sources = Array.from(new Set(newsItems.map((item) => item.sourceName).filter(Boolean))).sort();
  sourceFilter.innerHTML = "";
  const allOption = document.createElement("option");
  allOption.value = "all";
  allOption.textContent = TEXT.all;
  sourceFilter.appendChild(allOption);
  sources.forEach((source) => {
    const option = document.createElement("option");
    option.value = source;
    option.textContent = source;
    sourceFilter.appendChild(option);
  });
}

function setActivePreset(value) {
  presetButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.days === value);
  });
}

function initDateRange(newsItems, days = 30) {
  const dates = newsItems.map((item) => item.date).filter(Boolean).sort();
  if (!dates.length) return;
  const latest = dates[dates.length - 1];
  if (days === "all") {
    startDateFilter.value = "";
    endDateFilter.value = "";
    setActivePreset("all");
    return;
  }
  const start = new Date(`${latest}T00:00:00`);
  start.setDate(start.getDate() - Number(days));
  startDateFilter.value = start.toISOString().slice(0, 10);
  endDateFilter.value = latest;
  setActivePreset(String(days));
}

function readFilterControls() {
  let startDate = startDateFilter.value || "";
  let endDate = endDateFilter.value || "";
  if (startDate && endDate && startDate > endDate) {
    [startDate, endDate] = [endDate, startDate];
    startDateFilter.value = startDate;
    endDateFilter.value = endDate;
  }
  return {
    category: categoryFilter.value,
    grade: gradeFilter.value,
    source: sourceFilter.value,
    startDate,
    endDate,
    search: searchInput.value.trim().toLowerCase(),
    sort: sortFilter.value
  };
}

function applyCurrentFilters(newsItems) {
  appliedFilters = readFilterControls();
  renderNews(getFilteredNews(newsItems));
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
    const tagLabels = tags.map((tag) => TAG_LABELS[String(tag).toLowerCase()] || tag);
    const safeUrl = String(item.sourceUrl || "#");
    const card = document.createElement("article");
    card.className = "card";
    card.innerHTML = `
      <div class="meta">
        <span class="chip">${escapeHtml(item.category)}</span>
        <span class="chip grade-${escapeHtml(item.sourceGrade)}">${escapeHtml(item.sourceGrade)}${TEXT.gradeSuffix}</span>
        <span class="chip">${TEXT.importance} ${escapeHtml(item.importance || 0)}</span>
        <span class="chip">${TEXT.readingScore} ${escapeHtml(item.readingScore || 0)}</span>
        <span class="chip quality-${escapeHtml(item.qualityType || "general")}">${escapeHtml(item.qualityLabelZh || "\u4e00\u822c\u52a8\u6001")}</span>
        <span class="chip">${TEXT.qualityScore} ${escapeHtml(item.qualityScore || 0)}</span>
        <span>${escapeHtml(item.date)}</span>
      </div>
      <div class="card-body">
        ${renderVisual(item)}
        <div class="card-copy">
          <h3>${escapeHtml(item.titleZh || item.title)}</h3>
          <p>${escapeHtml(item.summaryZh || item.summary)}</p>
          ${renderKeyPoints(item.keyPointsZh || item.keyPoints)}
          <p class="tagline">${TEXT.tags}: ${escapeHtml(tagLabels.join(" / "))}</p>
          <p class="read-more-note">${TEXT.readMoreNote}</p>
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

function inSelectedTimeRange(dateValue, filters) {
  const date = String(dateValue || "").slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
  if (filters.startDate && date < filters.startDate) return false;
  if (filters.endDate && date > filters.endDate) return false;
  return true;
}

function getFilteredNews(newsItems) {
  const filters = appliedFilters || readFilterControls();

  const filtered = newsItems.filter((item) => {
    const categoryMatch = filters.category === "all" || item.category === filters.category;
    const gradeMatch = filters.grade === "all" || item.sourceGrade === filters.grade;
    const sourceMatch = filters.source === "all" || item.sourceName === filters.source;
    const timeMatch = inSelectedTimeRange(item.date, filters);
    const tags = Array.isArray(item.tags) ? item.tags.join(" ") : "";
    const keyPoints = Array.isArray(item.keyPoints) ? item.keyPoints.join(" ") : "";
    const textBlob = `${item.title} ${item.titleZh || ""} ${item.summary} ${item.summaryZh || ""} ${item.sourceName} ${tags} ${keyPoints}`.toLowerCase();
    const searchMatch = !filters.search || textBlob.includes(filters.search);
    return categoryMatch && gradeMatch && sourceMatch && timeMatch && searchMatch;
  });

  if (filters.sort === "importance") {
    filtered.sort((a, b) => (b.importance || 0) - (a.importance || 0));
  } else {
    filtered.sort((a, b) => String(b.date).localeCompare(String(a.date)));
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
  const markManualDate = () => setActivePreset("");
  [startDateFilter, endDateFilter].forEach((el) => el.addEventListener("input", () => {
    markManualDate();
  }));
  presetButtons.forEach((button) => {
    button.addEventListener("click", () => {
      initDateRange(newsItems, button.dataset.days);
    });
  });
  document.querySelectorAll(".date-picker-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.target);
      if (input && typeof input.showPicker === "function") {
        input.showPicker();
      } else if (input) {
        input.focus();
      }
    });
  });
  applyBtn.addEventListener("click", () => applyCurrentFilters(newsItems));
  searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") applyCurrentFilters(newsItems);
  });
  resetBtn.addEventListener("click", () => {
    categoryFilter.value = "all";
    gradeFilter.value = "all";
    sourceFilter.value = "all";
    initDateRange(newsItems, 30);
    sortFilter.value = "latest";
    searchInput.value = "";
    applyCurrentFilters(newsItems);
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
  initSourceOptions(newsItems);
  initDateRange(newsItems);
  updateKpis(newsItems);
  bindEvents(newsItems);
  appliedFilters = readFilterControls();
  renderNews(getFilteredNews(newsItems));
  await renderSourcePools();
}

init();
