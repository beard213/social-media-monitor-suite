const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const state = {
  overview: null,
  catalog: null,
  health: null,
  contract: null,
  feed: [],
  accounts: [],
  tasks: [],
  contents: [],
  selectedAccount: "",
  feedKind: "",
};

const viewTitles = {
  overview: "态势总览大屏",
  feed: "评论弹幕实时监控",
  accounts: "风险账号处置",
  analysis: "AI智能研判",
  topics: "话题溯源分析",
  tasks: "搜索与直播接入",
  discovery: "内容发现与筛选",
  jobs: "后台任务队列",
  system: "接口与系统配置",
};
const platformNames = { douyin: "抖音", kuaishou: "快手", demo: "演示" };
const riskNames = { high: "高风险", medium: "中风险", low: "低风险", normal: "正常", pending: "待研判" };
const filterNames = { kept: "已保留", needs_review: "待复核", advertising: "广告", irrelevant: "无关", pending: "待判断" };
const jobNames = { discovery: "关键词发现", comments: "评论采集", relations: "公开关系扩列", expand: "内容线索扩展", audit_text: "文字检测", capture: "媒体采集", push: "结果推送", live_segment: "直播分片" };

function esc(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}
function fmtNum(value) {
  const number = Number(value || 0);
  if (number >= 100000000) return `${(number / 100000000).toFixed(1)}亿`;
  if (number >= 10000) return `${(number / 10000).toFixed(1)}万`;
  return number.toLocaleString("zh-CN");
}
function fmtDate(value, withDate = true) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return esc(value);
  return new Intl.DateTimeFormat("zh-CN", { month: withDate ? "2-digit" : undefined, day: withDate ? "2-digit" : undefined, hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(date);
}
function initials(alias) {
  const text = String(alias || "匿").replace(/^user_/, "");
  return text.slice(0, 1).toUpperCase();
}
function splitWords(value) {
  return String(value || "").split(/[，,\n]/).map((x) => x.trim()).filter(Boolean);
}
function toast(message, type = "success") {
  const node = document.createElement("div");
  node.className = `toast ${type}`;
  node.textContent = message;
  $("#toast-stack").appendChild(node);
  setTimeout(() => node.remove(), 3600);
}
async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `${response.status} ${response.statusText}`);
  return data;
}
function openModal() { $("#detail-modal").classList.add("open"); $("#detail-modal").setAttribute("aria-hidden", "false"); }
function closeModal() { $("#detail-modal").classList.remove("open"); $("#detail-modal").setAttribute("aria-hidden", "true"); }
function safeUrl(value) { try { const url = new URL(value); return ["http:", "https:"].includes(url.protocol) ? url.toString() : ""; } catch { return ""; } }

function updateClock() {
  const now = new Date();
  $("#clock-date").textContent = new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", weekday: "short" }).format(now);
  $("#clock-time").textContent = new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(now);
}
function showView(name) {
  $$(".view").forEach((node) => node.classList.toggle("active", node.id === `view-${name}`));
  $$(".nav-item").forEach((node) => node.classList.toggle("active", node.dataset.view === name));
  $("#page-title").textContent = viewTitles[name] || "监测中心";
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (name === "feed") loadFeed();
  if (name === "accounts") loadAccounts();
  if (name === "analysis") loadAnalysisSelector();
  if (name === "topics") loadTopics();
  if (name === "tasks") loadTasks();
  if (name === "discovery") loadContents();
  if (name === "jobs") loadJobs();
  if (name === "system") loadSystem();
}

function metricCard(value, label, hint = "", tone = "") {
  return `<div class="metric-card ${tone}"><b>${esc(value)}</b><span>${esc(label)}</span><small>${esc(hint)}</small></div>`;
}
function renderOverview() {
  const data = state.overview;
  if (!data) return;
  const m = data.metrics;
  $("#hero-metrics").innerHTML = [
    [fmtNum(m.today_alerts), "今日预警", "red"], [fmtNum(m.pending_actions), "待处置", "orange"], [fmtNum(m.online_reviewers), "在线审核员", ""], [`${m.accuracy}%`, "处置率", "green"],
  ].map(([value, label, tone]) => `<div class="hero-metric ${tone}"><b>${value}</b><span>${label}</span></div>`).join("");

  const cloud = data.word_cloud?.length ? data.word_cloud : [{ text: "等待真实接口", weight: 8, tone: "info" }, { text: "抖音", weight: 5, tone: "danger" }, { text: "快手", weight: 4, tone: "warn" }];
  const maxWeight = Math.max(...cloud.map((x) => x.weight || 1), 1);
  $("#word-cloud").innerHTML = cloud.map((item, index) => {
    const size = 12 + Math.round((item.weight / maxWeight) * 24);
    const rotation = index % 9 === 0 ? "transform:rotate(-4deg)" : index % 11 === 0 ? "transform:rotate(4deg)" : "";
    return `<span class="cloud-word ${esc(item.tone)}" style="font-size:${size}px;${rotation}" data-topic="${esc(item.text)}">${esc(item.text)}</span>`;
  }).join("");

  $("#overview-topics").innerHTML = data.topics?.length ? data.topics.map((item) => `<div class="topic-item"><b>#${esc(item.label)}</b><div class="topic-meta"><span>热度 ${fmtNum(item.heat)}</span><span class="negative-pill">负向 ${item.negative_rate}%</span><span>${fmtDate(item.latest_at)}</span></div></div>`).join("") : `<div class="empty-card">暂无话题数据，运行监测任务后生成</div>`;

  $("#overview-accounts").innerHTML = data.risk_accounts?.length ? data.risk_accounts.map((item, index) => `<div class="rank-row ${item.risk_level}" data-account="${esc(item.alias)}"><span class="rank-num">${index + 1}</span><span class="avatar">${esc(initials(item.alias))}</span><div><span class="name">${esc(item.alias)}</span><small>${item.content_count}条公开内容 · ${esc((item.labels || []).slice(0, 2).join("、") || "待研判")}</small></div><span class="risk-score">${item.risk_score}</span></div>`).join("") : `<div class="empty-card">暂无账号汇总</div>`;

  const chart = data.hourly_alerts || [];
  const maxBar = Math.max(...chart.flatMap((x) => [x.discovered, x.interaction, x.high]), 1);
  $("#hourly-chart").innerHTML = chart.map((item) => `<div class="bar-group" title="${esc(item.label)} 发现${item.discovered} 互动${item.interaction} 高风险${item.high}"><i class="bar" style="height:${Math.max(2, item.discovered / maxBar * 100)}%"></i><i class="bar interaction" style="height:${Math.max(2, item.interaction / maxBar * 100)}%"></i><i class="bar high" style="height:${Math.max(2, item.high / maxBar * 100)}%"></i><span>${esc(item.label)}</span></div>`).join("");

  $("#activity-logs").innerHTML = data.logs?.length ? data.logs.map((item) => `<div class="log-item ${esc(item.level)}"><time>[${fmtDate(item.time, false)}]</time>${esc(item.message)}</div>`).join("") : `<div class="empty-card">暂无运行日志</div>`;
  renderConnectorMini(data.platforms || {});
}
function renderConnectorMini(platforms) {
  $("#overview-connectors").innerHTML = Object.entries(platforms).map(([name, info]) => `<div class="connector-mini"><span class="platform-logo ${name}">${esc(platformNames[name] || name)}</span><div><b>${esc(platformNames[name] || name)}连接器</b><small>${info.configured ? esc(info.base_url || info.mode) : "接口空位已保留，等待授权服务地址"}</small></div><span class="connector-state ${info.enabled ? "ok" : ""}">${info.enabled ? "已配置" : "待接入"}</span></div>`).join("");
}

async function loadOverview() {
  state.overview = await api("/console/overview");
  renderOverview();
}

function feedStats(rows) {
  const high = rows.filter((x) => x.risk_level === "high").length;
  const medium = rows.filter((x) => x.risk_level === "medium").length;
  const comments = rows.filter((x) => x.kind === "comment").length;
  const live = rows.length - comments;
  const accounts = new Set(rows.map((x) => x.author_alias)).size;
  $("#feed-metrics").innerHTML = [
    metricCard(high, "待审高风险", high ? "需要人工复核" : "当前无高风险", "red"),
    metricCard(fmtNum(rows.length), "当前消息", "已加载的实时记录", "orange"),
    metricCard(fmtNum(state.overview?.metrics?.total_interactions || rows.length), "累计互动", "评论＋直播事件"),
    metricCard(`${state.overview?.metrics?.accuracy || 0}%`, "AI识别参考率", "以人工复核结果校准", "green"),
    metricCard(medium, "中风险消息", "建议抽查", "orange"),
    metricCard(accounts, "涉及账号别名", "匿名化公开账号"),
  ].join("");
  return { high, medium, comments, live, accounts };
}
function renderFeed() {
  const query = $("#feed-search").value.trim().toLowerCase();
  let rows = state.feed;
  if (state.feedKind) rows = rows.filter((item) => state.feedKind === "live_message" ? item.kind !== "comment" : item.kind === state.feedKind);
  if (query) rows = rows.filter((item) => `${item.content_title} ${item.author_alias} ${item.text}`.toLowerCase().includes(query));
  feedStats(rows);
  const grouped = new Map();
  state.feed.forEach((item) => {
    const key = item.content_id;
    const current = grouped.get(key) || { content_id: key, title: item.content_title, platform: item.platform, count: 0, risk: 0 };
    current.count += 1; current.risk = Math.max(current.risk, item.risk_score); grouped.set(key, current);
  });
  $("#feed-content-list").innerHTML = [...grouped.values()].sort((a, b) => b.risk - a.risk).map((item) => `<div class="room-card ${item.risk >= 80 ? "high" : ""}" data-feed-content="${item.content_id}"><div class="room-card-head"><span class="avatar">${esc(platformNames[item.platform]?.slice(0,1) || "媒")}</span><div><b>${esc(item.title || `内容${item.content_id}`)}</b><small>${esc(platformNames[item.platform] || item.platform)} · ${item.count}条消息</small></div><span class="room-risk">${item.risk}</span></div></div>`).join("") || `<div class="empty-card">暂无实时内容</div>`;
  $("#feed-list").innerHTML = rows.map((item) => `<article class="message-card ${item.risk_level}" data-account="${esc(item.author_alias)}"><div class="message-head"><span class="avatar">${esc(initials(item.author_alias))}</span><b>${esc(item.author_alias)}</b><span class="platform-chip">${esc(platformNames[item.platform] || item.platform)}</span><span class="kind-chip">${item.kind === "comment" ? "评论" : esc(item.kind)}</span><span class="risk-chip ${item.risk_level}">${esc(riskNames[item.risk_level])} ${item.risk_score}</span><time>${fmtDate(item.event_time, false)}</time></div><div class="message-text">${highlightText(item.text, item.risk_words)}</div><div class="message-footer"><span>${esc(item.content_title)} · ${item.like_count || 0}赞</span><div class="message-actions"><button data-feed-review="normal" data-account="${esc(item.author_alias)}">标记正常</button><button data-feed-review="high" data-account="${esc(item.author_alias)}">确认风险</button><button data-view-account="${esc(item.author_alias)}">查看账号</button></div></div></article>`).join("") || `<div class="empty-card large">当前筛选条件下暂无评论或弹幕</div>`;
}
function highlightText(text, words = []) {
  let result = esc(text);
  (words || []).filter(Boolean).slice(0, 8).forEach((word) => {
    const safe = esc(word).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    result = result.replace(new RegExp(safe, "gi"), (match) => `<span class="highlight">${match}</span>`);
  });
  return result;
}
async function loadFeed() {
  const params = new URLSearchParams({ limit: "300" });
  if ($("#feed-platform").value) params.set("platform", $("#feed-platform").value);
  if ($("#feed-risk").value) params.set("risk_level", $("#feed-risk").value);
  state.feed = await api(`/console/feed?${params}`);
  renderFeed();
}
async function showFeedAccount(alias) {
  state.selectedAccount = alias;
  const detail = await api(`/console/risk-accounts/${encodeURIComponent(alias)}`);
  $("#feed-account-detail").className = "";
  $("#feed-account-detail").innerHTML = `<div class="detail-block"><div class="avatar">${esc(initials(alias))}</div><h4>${esc(alias)}</h4><p>${esc(detail.summary)}</p></div><div class="detail-block"><h4>风险评分</h4><div class="risk-score-big">${detail.risk_score}</div><p>${esc(detail.risk_label)} · ${detail.content_count}条公开内容</p></div><div class="detail-block"><h4>主要信号</h4><div class="signal-tags">${(detail.profile_summary.top_signals || []).map((x) => `<span class="signal-tag">${esc(x)}</span>`).join("") || "无"}</div></div><button class="btn ghost" data-open-analysis="${esc(alias)}">进入完整研判</button>`;
}

function renderAccounts() {
  const filter = $("#account-risk-filter").value;
  const rows = filter ? state.accounts.filter((x) => x.risk_level === filter) : state.accounts;
  $("#account-queue").innerHTML = rows.map((item) => `<div class="account-card ${item.risk_level} ${state.selectedAccount === item.alias ? "active" : ""}" data-account-select="${esc(item.alias)}"><span class="avatar">${esc(initials(item.alias))}</span><div><b>${esc(item.alias)}</b><small>${esc(item.risk_label)} · ${item.content_count}条内容 · ${esc((item.labels || []).slice(0,2).join("、") || "待研判")}</small></div><span class="room-risk">${item.risk_score}</span></div>`).join("") || `<div class="empty-card">暂无账号记录</div>`;
  const select = $("#analysis-account-select");
  select.innerHTML = `<option value="">选择账号</option>${state.accounts.map((x) => `<option value="${esc(x.alias)}" ${x.alias === state.selectedAccount ? "selected" : ""}>${esc(x.alias)} · ${x.risk_score}分</option>`).join("")}`;
}
async function loadAccounts() {
  state.accounts = await api("/console/risk-accounts?limit=200");
  if (!state.selectedAccount && state.accounts.length) state.selectedAccount = state.accounts[0].alias;
  renderAccounts();
  if (state.selectedAccount) await showAccountAnalysis(state.selectedAccount);
}
async function showAccountAnalysis(alias) {
  state.selectedAccount = alias;
  renderAccounts();
  const detail = await api(`/console/risk-accounts/${encodeURIComponent(alias)}`);
  $("#analysis-generated").textContent = `生成时间：${fmtDate(new Date().toISOString())}`;
  const body = $("#account-analysis-body"); body.className = "account-analysis-body";
  body.innerHTML = `<div class="account-summary"><div class="summary-box"><h4>账号画像摘要</h4><p><b>${esc(alias)}</b><br>${esc(detail.summary)}<br>${esc(detail.profile_summary.basis)}</p></div><div class="summary-box"><h4>本次风险</h4><div class="risk-score-big">${detail.risk_score}</div><p>${esc(detail.risk_label)} · 平台 ${detail.platforms.map((x) => platformNames[x] || x).join("、")}</p></div><div class="summary-box"><h4>主要风险信号</h4><div class="signal-tags">${detail.profile_summary.top_signals.map((x) => `<span class="signal-tag">${esc(x)}</span>`).join("") || "暂无标签"}</div></div><div class="summary-box"><h4>传播互动</h4><p>播放/观看 ${fmtNum(detail.engagement.views)}<br>点赞 ${fmtNum(detail.engagement.likes)} · 评论 ${fmtNum(detail.engagement.comments)} · 分享 ${fmtNum(detail.engagement.shares)}</p></div></div><h4>公开内容时间线</h4><div class="timeline-list">${detail.timeline.map((item) => `<div class="timeline-item"><b>${esc(item.title)}</b><p>${fmtDate(item.time)} · ${esc(platformNames[item.platform] || item.platform)} · 风险${item.risk_score}分</p><div class="signal-tags">${(item.labels || []).map((x) => `<span class="signal-tag">${esc(x)}</span>`).join("")}</div></div>`).join("") || `<div class="empty-card">暂无时间线</div>`}</div>`;
  $("#account-quick-tags").innerHTML = detail.profile_summary.top_signals.map((x) => `<span class="signal-tag">${esc(x)}</span>`).join("") || `<span class="signal-tag">待人工补充</span>`;
}
async function reviewAccount(alias, status) {
  if (!alias) return toast("请先选择账号", "error");
  await api(`/console/risk-accounts/${encodeURIComponent(alias)}/review?status=${status}`, { method: "POST" });
  toast(`已将 ${alias} 标记为${riskNames[status] || status}`);
  await Promise.all([loadAccounts(), loadOverview(), loadFeed()]);
}

async function loadAnalysisSelector() {
  if (!state.accounts.length) state.accounts = await api("/console/risk-accounts?limit=200");
  renderAccounts();
  if (state.selectedAccount) await renderAnalysisDashboard(state.selectedAccount);
}
async function renderAnalysisDashboard(alias) {
  if (!alias) { $("#analysis-dashboard").innerHTML = `<div class="panel empty-card large">请先选择一个风险账号</div>`; return; }
  state.selectedAccount = alias;
  const detail = await api(`/console/risk-accounts/${encodeURIComponent(alias)}`);
  const maxEngagement = Math.max(detail.engagement.views, detail.engagement.likes, detail.engagement.comments, detail.engagement.shares, 1);
  $("#analysis-dashboard").innerHTML = `<article class="panel"><div class="panel-title"><span>◉</span><div><h3>综合风险评分</h3><p>${esc(detail.risk_label)} · 模型与人工结果综合</p></div></div><div class="gauge"></div><div class="gauge-value">${detail.risk_score}</div><p class="empty-card">评分仅用于内容复核优先级，不代表现实身份判断。</p></article><article class="panel"><div class="panel-title"><span>♟</span><div><h3>公开账号摘要</h3><p>${esc(alias)}</p></div></div><div class="account-summary"><div class="summary-box"><h4>内容数量</h4><div class="risk-score-big">${detail.content_count}</div></div><div class="summary-box"><h4>涉及平台</h4><p>${detail.platforms.map((x) => platformNames[x] || x).join("、")}</p></div><div class="summary-box span-2"><h4>主要信号</h4><div class="signal-tags">${detail.profile_summary.top_signals.map((x) => `<span class="signal-tag">${esc(x)}</span>`).join("") || "暂无"}</div></div></div></article><article class="panel"><div class="panel-title"><span>▥</span><div><h3>互动传播结构</h3><p>基于连接器已返回的公开统计字段</p></div></div>${Object.entries(detail.engagement).map(([key,value]) => `<div class="connector-check"><span>${({views:"播放/观看",likes:"点赞",comments:"评论",shares:"分享"})[key]}</span><div style="width:65%;height:8px;background:#09111b;border-radius:8px;overflow:hidden"><i style="display:block;height:100%;width:${Math.max(2,value/maxEngagement*100)}%;background:var(--cyan)"></i></div><b>${fmtNum(value)}</b></div>`).join("")}</article><article class="panel"><div class="panel-title"><span>⚑</span><div><h3>研判说明</h3><p>可解释性输出</p></div></div><p style="font-size:10px;line-height:1.8;color:#a3b3c8">${esc(detail.summary)} 系统依据已接入的公开内容、检测标签、风险词、互动数量和人工复核状态计算优先级。${esc(detail.profile_summary.basis)}</p><div class="signal-tags">${(detail.labels || []).map((x) => `<span class="signal-tag">${esc(x)}</span>`).join("")}</div></article><article class="panel wide"><div class="panel-title"><span>⌘</span><div><h3>公开账号关系扩列</h3><p>评论区、高频互动和平台公开关注/朋友关系；仅显示连接器返回的公开线索</p></div></div><div class="relation-network"><div class="relation-center"><span class="avatar">${esc(initials(alias))}</span><b>${esc(alias)}</b></div><div class="relation-node-grid">${(detail.relation_leads || []).map((item) => `<div class="relation-node"><span>${esc(({following:"关注",follower:"粉丝",friend:"朋友",frequent_commenter:"高频评论",related_account:"关联账号"})[item.lead_type] || item.lead_type)}</span><b>${esc(item.label)}</b><small>证据 ${item.evidence_count} 条</small></div>`).join("") || `<div class="empty-card">尚未获得公开关系数据；赵帅填写 /v1/relations 后自动显示</div>`}</div></div></article><article class="panel wide"><div class="panel-title"><span>▤</span><div><h3>违规/风险内容切片时间线</h3><p>按公开内容发布时间排列</p></div></div><div class="timeline-list">${detail.timeline.map((item) => `<div class="timeline-item"><b>${esc(item.title)}</b><p>${fmtDate(item.time)} · ${esc(platformNames[item.platform] || item.platform)} · ${esc(item.content_type)} · 置信风险 ${item.risk_score}</p><div class="signal-tags">${[...(item.labels || []), ...(item.risk_words || [])].slice(0,8).map((x) => `<span class="signal-tag">${esc(x)}</span>`).join("")}</div>${safeUrl(item.source_url) ? `<p><a href="${esc(safeUrl(item.source_url))}" target="_blank" rel="noreferrer">打开公开来源</a></p>` : ""}</div>`).join("") || `<div class="empty-card">暂无内容时间线</div>`}</div></article>`;
}

async function loadTopics() {
  const data = await api("/console/topics?limit=50");
  $("#topic-table").innerHTML = data.topics.length ? `<table class="table-grid"><thead><tr><th>排名</th><th>话题</th><th>热度</th><th>负向占比</th><th>最近发现</th><th>操作</th></tr></thead><tbody>${data.topics.map((item,index) => `<tr><td>${index+1}</td><td class="table-title">#${esc(item.label)}</td><td>${fmtNum(item.heat)}</td><td><span class="tag ${item.negative_rate >= 70 ? "high" : item.negative_rate >= 45 ? "medium" : "normal"}">${item.negative_rate}%</span></td><td>${fmtDate(item.latest_at)}</td><td><button class="btn ghost" data-topic-open="${esc(item.label)}">查看内容</button></td></tr>`).join("")}</tbody></table>` : `<div class="empty-card large">暂无话题数据</div>`;
  const maxWeight = Math.max(...data.word_cloud.map((x) => x.weight || 1), 1);
  $("#topic-cloud").innerHTML = data.word_cloud.map((item,index) => `<span class="cloud-word ${esc(item.tone)}" style="font-size:${13 + Math.round(item.weight / maxWeight * 24)}px" data-topic="${esc(item.text)}">${esc(item.text)}</span>`).join("") || `<div class="empty-card">暂无标签</div>`;
}

function populateCatalog() {
  if (!state.catalog) return;
  $("#topic-template").innerHTML = state.catalog.topics.map((x) => `<option value="${esc(x.id)}">${esc(x.name)}</option>`).join("");
  const regionOptions = `<option value="">不限区域</option>${state.catalog.regions.map((x) => `<option value="${esc(x.id)}">${esc(x.name)}</option>`).join("")}`;
  $("#region-select").innerHTML = regionOptions;
  if ($("#live-region-select")) $("#live-region-select").innerHTML = regionOptions;
  $("#platform-select").innerHTML = Object.entries(state.catalog.platforms).map(([id, info]) => `<option value="${id}" ${id === "demo" ? "selected" : ""}>${esc(platformNames[id] || id)}${info.enabled ? "" : "（接口待接入）"}</option>`).join("");
  $("#interval-select").innerHTML = state.catalog.intervals.map((x) => `<option value="${x.seconds}">${esc(x.name)}</option>`).join("");
}
async function loadCatalog() { state.catalog = await api("/catalog"); populateCatalog(); }
function applyTopicTemplate() {
  const topic = state.catalog?.topics?.find((item) => item.id === $("#topic-template").value);
  if (!topic || topic.id === "custom") return;
  $("#include-keywords").value = (topic.include_keywords || []).join("、");
  $("#exclude-keywords").value = (topic.exclude_keywords || []).join("、");
  if (!$("#task-name").value.trim()) $("#task-name").value = `${topic.name}监测`;
}

function resetTaskForm() { $("#task-form").reset(); populateCatalog(); }
async function submitTask(event) {
  event.preventDefault();
  const platforms = [...$("#platform-select").selectedOptions].map((x) => x.value);
  const contentTypes = $$('input[name="content-type"]:checked').map((x) => x.value);
  const region = $("#region-select").value;
  if (!platforms.length || !contentTypes.length) return toast("至少选择一个平台和内容类型", "error");
  const body = {
    name: $("#task-name").value.trim(), platforms, content_types: contentTypes,
    include_keywords: splitWords($("#include-keywords").value), exclude_keywords: splitWords($("#exclude-keywords").value),
    interval_seconds: Number($("#interval-select").value), enabled: true, topic_template: $("#topic-template").value || "custom",
    regions: region ? [region] : [], keyword_match_mode: "any", time_range_hours: Number($("#time-range").value),
    sort_by: $("#sort-by").value, result_limit: Number($("#result-limit").value), collect_comments: $("#collect-comments").checked,
    expand_related: $("#expand-related").checked, auto_audit: $("#auto-audit").checked, auto_capture: $("#auto-capture").checked,
    auto_push: $("#auto-push").checked, push_after_review: true, notes: "由监测控制台创建",
  };
  if (!body.name || !body.include_keywords.length) return toast("任务名称和关注关键词不能为空", "error");
  await api("/tasks", { method: "POST", body: JSON.stringify(body) });
  toast("监测任务已创建"); resetTaskForm(); $("#task-builder").hidden = true; await loadTasks(); await loadOverview();
}
async function submitLiveMonitor(event) {
  event.preventDefault();
  const roomId = $("#live-room-id").value.trim();
  if (!roomId) return toast("请输入直播间ID", "error");
  const region = $("#live-region-select").value;
  const body = {
    platform: $("#live-platform").value,
    room_id: roomId,
    title: $("#live-title").value.trim(),
    stream_url: $("#live-stream-url").value.trim(),
    keywords: splitWords($("#live-keywords").value),
    regions: region ? [region] : [],
    segment_seconds: Number($("#live-segment-seconds").value),
    auto_capture: $("#live-auto-capture").checked,
    auto_push: $("#live-auto-push").checked,
    notes: "由前端直播ID接入页面创建",
  };
  const resultBox = $("#live-start-result");
  resultBox.className = "live-start-result loading";
  resultBox.textContent = "正在登记直播ID并解析直播源……";
  try {
    const result = await api("/live-monitor/start", { method: "POST", body: JSON.stringify(body) });
    resultBox.className = `live-start-result ${result.ready_for_capture ? "success" : "pending"}`;
    resultBox.innerHTML = `<b>${esc(result.message)}</b><span>内容ID：${result.content_id} · 会话ID：${result.live_session_id} · 来源：${esc(result.stream_source)}</span>${result.resolve_errors?.length ? `<small>${esc(result.resolve_errors.join("；"))}</small>` : ""}`;
    toast(result.message, result.ready_for_capture ? "success" : "error");
    await Promise.all([loadContents(), loadJobs(), loadOverview(), loadHealthBadge()]);
  } catch (error) {
    resultBox.className = "live-start-result error";
    resultBox.textContent = `启动失败：${error.message}`;
    toast(error.message, "error");
  }
}

async function loadTasks() {
  state.tasks = await api("/tasks");
  $("#task-table").innerHTML = state.tasks.length ? `<table class="table-grid"><thead><tr><th>任务</th><th>平台/类型</th><th>关键词</th><th>频率</th><th>内容/队列</th><th>状态</th><th>操作</th></tr></thead><tbody>${state.tasks.map((task) => `<tr><td><span class="table-title">${esc(task.name)}</span><span class="table-sub">创建 ${fmtDate(task.created_at)}</span></td><td>${task.platforms.map((x) => platformNames[x] || x).join("、")}<span class="table-sub">${task.content_types.join("＋")}</span></td><td>${esc(task.include_keywords.slice(0,4).join("、"))}</td><td>${Math.round(task.interval_seconds/60)}分钟</td><td>${task.content_count || 0}条 / ${task.pending_jobs || 0}待处理</td><td><span class="tag ${task.enabled ? "success" : "normal"}">${task.enabled ? "启用" : "暂停"}</span></td><td><button class="btn primary" data-task-run="${task.id}">立即执行</button> <button class="btn secondary" data-task-toggle="${task.id}">${task.enabled ? "暂停" : "启用"}</button> <button class="btn danger" data-task-delete="${task.id}">删除</button></td></tr>`).join("")}</tbody></table>` : `<div class="empty-card large">暂无任务，点击“新建任务”开始配置</div>`;
}
async function taskAction(id, action) {
  if (action === "delete") { if (!confirm("确定删除该监测任务？")) return; await api(`/tasks/${id}`, { method: "DELETE" }); toast("任务已删除"); }
  else { await api(`/tasks/${id}/${action}`, { method: "POST" }); toast(action === "run" ? "已加入关键词发现队列" : "任务状态已更新"); }
  await Promise.all([loadTasks(), loadJobs(), loadOverview()]);
}

async function loadContents(topic = "") {
  const params = new URLSearchParams({ limit: "300" });
  const values = { query: $("#content-query").value.trim(), platform: $("#content-platform").value, content_type: $("#content-type").value, filter_status: $("#content-status").value };
  Object.entries(values).forEach(([key,value]) => value && params.set(key,value));
  if (topic) params.set("query", topic);
  state.contents = await api(`/contents?${params}`);
  $("#content-results").innerHTML = state.contents.map((item) => `<article class="content-card"><div class="content-cover">${item.cover_url ? `<img src="${esc(item.cover_url)}" alt="" style="width:100%;height:100%;object-fit:cover" onerror="this.remove()">` : item.content_type === "live" ? "◉ LIVE" : "▶ VIDEO"}</div><div class="content-body"><h4>${esc(item.title || "无标题公开内容")}</h4><p>${esc((item.description || "").slice(0,130))}</p><div class="content-tags"><span class="tag">${esc(platformNames[item.platform] || item.platform)}</span><span class="tag ${item.filter_status}">${esc(filterNames[item.filter_status] || item.filter_status)}</span><span class="tag">${esc(item.pipeline_stage)}</span>${(item.matched_keywords || []).slice(0,3).map((x) => `<span class="tag">${esc(x)}</span>`).join("")}</div><div class="content-meta"><span>${esc(item.author_alias)} · ${fmtDate(item.published_at || item.first_seen_at)}</span><span>${item.comment_count}评论</span></div><div class="content-actions"><button class="btn ghost" data-content-view="${item.id}">详情</button><button class="btn secondary" data-content-action="comments" data-content-id="${item.id}">抓评论</button><button class="btn secondary" data-content-action="relations" data-content-id="${item.id}">关系扩列</button><button class="btn secondary" data-content-action="audit" data-content-id="${item.id}">检测</button>${item.content_type === "live" ? `<button class="btn primary" data-content-action="capture" data-content-id="${item.id}">采集分片</button>` : ""}<button class="btn secondary" data-content-review="kept" data-content-id="${item.id}">保留</button><button class="btn danger" data-content-review="irrelevant" data-content-id="${item.id}">无关</button></div></div></article>`).join("") || `<div class="panel empty-card large" style="grid-column:1/-1">暂无内容。可先创建演示任务并运行，或配置抖音/快手授权连接器。</div>`;
}
async function contentAction(id, action) {
  const pathMap = { comments: "comments/fetch", relations: "relations/fetch", audit: "audit", capture: "capture", expand: "expand", push: "push" };
  const suffix = pathMap[action] || action;
  await api(`/contents/${id}/${suffix}`, { method: "POST" });
  toast("处理任务已加入队列");
  await loadJobs();
}
async function contentReview(id, status) { await api(`/contents/${id}/review?status=${status}`, { method: "POST" }); toast("内容复核状态已更新"); await Promise.all([loadContents(), loadOverview()]); }
async function viewContent(id) {
  const data = await api(`/contents/${id}`);
  const c = data.content;
  const relationNames = {
    comment_topic: "评论主题",
    hashtag: "话题标签",
    related_content: "关联公开内容",
    following: "公开关注",
    follower: "公开粉丝",
    friend: "公开朋友",
    frequent_commenter: "高频评论者",
    related_account: "关联公开账号",
  };
  $("#detail-body").innerHTML = `
    <h2>${esc(c.title || "内容详情")}</h2>
    <div class="detail-grid">
      <section class="detail-section"><h4>基本信息</h4><p>平台：${esc(platformNames[c.platform] || c.platform)}<br>类型：${esc(c.content_type)}<br>账号别名：${esc(c.author_alias)}<br>时间：${fmtDate(c.published_at || c.first_seen_at)}<br>区域：${esc((c.region_tags || []).join("、") || "未识别")}<br>状态：${esc(filterNames[c.filter_status] || c.filter_status)}<br>命中词：${esc((c.matched_keywords || []).join("、"))}</p>${safeUrl(c.source_url) ? `<a href="${esc(safeUrl(c.source_url))}" target="_blank" rel="noreferrer">打开公开来源</a>` : ""}</section>
      <section class="detail-section"><h4>内容描述</h4><p>${esc(c.description || "无")}</p></section>
      <section class="detail-section"><h4>公开评论（${data.comments.length}）</h4>${data.comments.map((x) => `<div class="comment-row"><b>${esc(x.author_alias)}</b> · ${x.like_count}赞<br>${esc(x.text)}</div>`).join("") || "暂无"}</section>
      <section class="detail-section"><h4>公开扩列线索（${data.leads.length}）</h4>${data.leads.map((x) => `<div class="comment-row"><b>${esc(relationNames[x.lead_type] || x.lead_type)}</b> · 证据${x.evidence_count}条<br>${esc(x.label)}</div>`).join("") || "暂无；可点击“抓评论”和“关系扩列”生成"}</section>
      <section class="detail-section"><h4>检测结果（${data.audits.length}）</h4>${data.audits.map((x) => `<div class="comment-row"><b>${esc(x.modality)}</b> · ${esc(x.status)} · ${x.confidence ?? "—"}<br>${esc((x.labels || []).join("、"))}</div>`).join("") || "暂无"}</section>
      <section class="detail-section"><h4>证据与推送</h4><p>证据文件：${data.evidence.length} 个<br>推送记录：${data.push_records.length} 条<br>当前阶段：${esc(c.pipeline_stage)}</p></section>
    </div>`;
  openModal();
}

async function loadJobs() {
  const params = new URLSearchParams({ limit: "300" });
  if ($("#job-status").value) params.set("status", $("#job-status").value);
  if ($("#job-type").value) params.set("job_type", $("#job-type").value);
  const rows = await api(`/jobs?${params}`);
  $("#job-table").innerHTML = rows.length ? `<table class="table-grid"><thead><tr><th>ID</th><th>类型</th><th>状态</th><th>目标</th><th>尝试</th><th>更新时间</th><th>错误</th></tr></thead><tbody>${rows.map((job) => `<tr><td>${job.id}</td><td>${esc(jobNames[job.job_type] || job.job_type)}</td><td><span class="tag ${job.status}">${esc(job.status)}</span></td><td>${job.payload.task_id ? `任务${job.payload.task_id}` : job.payload.content_id ? `内容${job.payload.content_id}` : "—"}</td><td>${job.attempts}/${job.max_attempts}</td><td>${fmtDate(job.updated_at || job.created_at)}</td><td title="${esc(job.last_error)}">${esc((job.last_error || "—").slice(0,90))}</td></tr>`).join("")}</tbody></table>` : `<div class="empty-card large">暂无后台任务</div>`;
}

function connectorCard(name, info) {
  const configured = Boolean(info.configured);
  return `<article class="connector-card"><div class="connector-card-head"><span class="platform-logo ${name}">${esc(platformNames[name] || name)}</span><div><h3>${esc(platformNames[name] || name)}连接器</h3><p>${name === "demo" ? "用于完整流程演示" : "真实平台凭证和调用逻辑隔离在独立授权服务中"}</p></div></div><div class="connector-checks"><div class="connector-check"><span>连接器URL</span><b class="${configured ? "ok" : "missing"}">${configured ? esc(info.base_url || "已配置") : "留空"}</b></div><div class="connector-check"><span>内部Token</span><b class="${info.token_configured ? "ok" : "missing"}">${info.token_configured ? "已配置" : "留空"}</b></div><div class="connector-check"><span>任务中心协议</span><b class="ok">已完成</b></div><div class="connector-check"><span>公开关系扩列</span><b class="ok">接口已预留</b></div><div class="connector-check"><span>平台官方API</span><b class="${name === "demo" ? "ok" : "missing"}">${name === "demo" ? "演示内置" : "等待权限"}</b></div></div>${name !== "demo" ? `<button class="btn ${configured ? "secondary" : "danger"}" data-test-connector="${name}" style="margin-top:12px;width:100%">${configured ? "测试连接" : "接口位置已空出"}</button>` : ""}</article>`;
}
async function loadSystem() {
  const [health, contract] = await Promise.all([api("/health"), api("/console/connector-contract")]);
  state.health = health; state.contract = contract;
  $("#connector-cards").innerHTML = Object.entries(health.platforms || {}).map(([name,info]) => connectorCard(name,info)).join("");
  $("#contract-list").innerHTML = contract.endpoints.map((item) => `<div class="contract-row"><span class="http-method">${esc(item.method)}</span><code>${esc(item.path)}</code><span>${esc(item.purpose)}</span></div>`).join("");
  $("#env-template").textContent = `# 任务中心 .env
DEMO_PROVIDER_ENABLED=true

# 抖音/快手连接器（赵帅填写）
DOUYIN_CONNECTOR_URL=${contract.environment.DOUYIN_CONNECTOR_URL}
DOUYIN_CONNECTOR_TOKEN=${contract.environment.DOUYIN_CONNECTOR_TOKEN}
KUAISHOU_CONNECTOR_URL=${contract.environment.KUAISHOU_CONNECTOR_URL}
KUAISHOU_CONNECTOR_TOKEN=${contract.environment.KUAISHOU_CONNECTOR_TOKEN}

# 已完成的直播ID监控服务桥接
LIVE_MONITOR_BRIDGE_URL=${contract.environment.LIVE_MONITOR_BRIDGE_URL}
LIVE_MONITOR_BRIDGE_TOKEN=${contract.environment.LIVE_MONITOR_BRIDGE_TOKEN}

# 推送给赵帅项目方
PUSH_TARGET_NAME=${contract.environment.PUSH_TARGET_NAME}
PUSH_EVENTS_URL=${contract.environment.PUSH_EVENTS_URL}
PUSH_MEDIA_URL=${contract.environment.PUSH_MEDIA_URL}

# 平台官方凭证仅放独立连接器服务
DOUYIN_CLIENT_KEY=
DOUYIN_CLIENT_SECRET=
DOUYIN_ACCESS_TOKEN=
DOUYIN_REFRESH_TOKEN=
DOUYIN_OPEN_ID=
KUAISHOU_APP_ID=
KUAISHOU_APP_SECRET=
KUAISHOU_ACCESS_TOKEN=`;
  $("#health-json").textContent = JSON.stringify(health, null, 2);
}
async function testConnector(platform) {
  try { const result = await api(`/console/connectors/${platform}/test`, { method: "POST" }); toast(result.ok ? `${platformNames[platform]}连接器正常` : `${platformNames[platform]}连接器未就绪：${result.message || "能力未配置"}`, result.ok ? "success" : "error"); } catch (error) { toast(error.message, "error"); }
}
async function loadHealthBadge() {
  try {
    const health = await api("/health"); state.health = health;
    const configured = Object.entries(health.platforms || {}).filter(([name, x]) => name !== "demo" && x.enabled).length;
    const badge = $("#environment-badge");
    if (configured) { badge.className = "status-badge ok"; badge.textContent = `${configured}个真实平台已配置`; }
    else if (health.live_monitor_bridge?.configured) { badge.className = "status-badge ok"; badge.textContent = "直播ID链路已配置"; }
    else { badge.className = "status-badge pending"; badge.textContent = "直播ID可登记 · 搜索接口待接入"; }
  } catch (error) { const badge = $("#environment-badge"); badge.className = "status-badge error"; badge.textContent = "系统连接失败"; }
}

function bindEvents() {
  $$(".nav-item").forEach((button) => button.addEventListener("click", () => showView(button.dataset.view)));
  $("#refresh-all").addEventListener("click", async () => { await loadAll(); toast("数据已刷新"); });
  $("#theme-toggle").addEventListener("click", () => {
    document.body.classList.toggle("presentation-bright");
    $("#theme-toggle").textContent = document.body.classList.contains("presentation-bright") ? "☀ 亮蓝模式" : "◐ 深蓝模式";
  });
  $("#screen-mode-btn").addEventListener("click", async () => {
    document.body.classList.toggle("screen-mode");
    if (document.body.classList.contains("screen-mode")) {
      try { await document.documentElement.requestFullscreen(); } catch (_) {}
    } else if (document.fullscreenElement) {
      await document.exitFullscreen();
    }
  });
  $("#feed-platform").addEventListener("change", loadFeed); $("#feed-risk").addEventListener("change", loadFeed); $("#feed-search").addEventListener("input", renderFeed);
  $$("[data-feed-kind]").forEach((button) => button.addEventListener("click", () => { $$("[data-feed-kind]").forEach((x) => x.classList.remove("active")); button.classList.add("active"); state.feedKind = button.dataset.feedKind; renderFeed(); }));
  $("#feed-batch").addEventListener("click", () => toast("请在具体账号条目中执行人工复核，避免批量误判", "error"));
  $("#account-risk-filter").addEventListener("change", renderAccounts); $("#refresh-accounts").addEventListener("click", loadAccounts);
  $$('[data-account-review]').forEach((button) => button.addEventListener("click", () => reviewAccount(state.selectedAccount, button.dataset.accountReview)));
  $("#open-analysis-view").addEventListener("click", () => { if (!state.selectedAccount) return toast("请先选择账号", "error"); showView("analysis"); renderAnalysisDashboard(state.selectedAccount); });
  $("#explain-account").addEventListener("click", () => { if (!state.selectedAccount) return toast("请先选择账号", "error"); toast("已生成基于公开内容信号的解释性研判摘要"); });
  $("#analysis-account-select").addEventListener("change", (event) => renderAnalysisDashboard(event.target.value)); $("#analysis-refresh").addEventListener("click", () => renderAnalysisDashboard($("#analysis-account-select").value));
  $("#refresh-topics").addEventListener("click", loadTopics);
  $("#toggle-task-builder").addEventListener("click", () => { const node = $("#task-builder"); node.hidden = !node.hidden; $("#toggle-task-builder").textContent = node.hidden ? "＋ 新建任务" : "收起配置"; });
  $("#task-form").addEventListener("submit", submitTask); $("#reset-task-form").addEventListener("click", resetTaskForm); $("#refresh-tasks").addEventListener("click", loadTasks);
  $("#topic-template").addEventListener("change", applyTopicTemplate);
  $("#live-id-form").addEventListener("submit", submitLiveMonitor);
  $("#search-contents").addEventListener("click", () => loadContents()); $("#reset-contents").addEventListener("click", () => { ["#content-query", "#content-platform", "#content-type", "#content-status"].forEach((x) => $(x).value = ""); loadContents(); });
  $("#content-query").addEventListener("keydown", (event) => { if (event.key === "Enter") loadContents(); });
  $("#job-status").addEventListener("change", loadJobs); $("#job-type").addEventListener("change", loadJobs); $("#refresh-jobs").addEventListener("click", loadJobs); $("#refresh-system").addEventListener("click", loadSystem);
  $$('[data-close-modal]').forEach((button) => button.addEventListener("click", closeModal)); $("#detail-modal").addEventListener("click", (event) => { if (event.target.id === "detail-modal") closeModal(); });

  document.addEventListener("click", async (event) => {
    const target = event.target.closest("[data-account],[data-account-select],[data-feed-review],[data-view-account],[data-open-analysis],[data-task-run],[data-task-toggle],[data-task-delete],[data-content-view],[data-content-action],[data-content-review],[data-test-connector],[data-topic-open],[data-topic],[data-feed-content]");
    if (!target) return;
    try {
      if (target.dataset.accountSelect) return showAccountAnalysis(target.dataset.accountSelect);
      if (target.dataset.account && target.classList.contains("rank-row")) {
        state.selectedAccount = target.dataset.account;
        showView("accounts");
        return loadAccounts();
      }
      if (target.dataset.account && !target.dataset.feedReview) return showFeedAccount(target.dataset.account);
      if (target.dataset.viewAccount) return showFeedAccount(target.dataset.viewAccount);
      if (target.dataset.openAnalysis) { state.selectedAccount = target.dataset.openAnalysis; showView("analysis"); return renderAnalysisDashboard(state.selectedAccount); }
      if (target.dataset.feedReview) return reviewAccount(target.dataset.account, target.dataset.feedReview);
      if (target.dataset.taskRun) return taskAction(target.dataset.taskRun, "run");
      if (target.dataset.taskToggle) return taskAction(target.dataset.taskToggle, "toggle");
      if (target.dataset.taskDelete) return taskAction(target.dataset.taskDelete, "delete");
      if (target.dataset.contentView) return viewContent(target.dataset.contentView);
      if (target.dataset.contentAction) return contentAction(target.dataset.contentId, target.dataset.contentAction);
      if (target.dataset.contentReview) return contentReview(target.dataset.contentId, target.dataset.contentReview);
      if (target.dataset.testConnector) return testConnector(target.dataset.testConnector);
      if (target.dataset.topicOpen || target.dataset.topic) { $("#content-query").value = target.dataset.topicOpen || target.dataset.topic; showView("discovery"); return loadContents(); }
      if (target.dataset.feedContent) { const id = Number(target.dataset.feedContent); state.feed = await api(`/console/feed?limit=300`); state.feed = state.feed.filter((x) => x.content_id === id); $("#feed-stream-title").textContent = state.feed[0]?.content_title || `内容 ${id}`; return renderFeed(); }
    } catch (error) { toast(error.message, "error"); }
  });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeModal(); });
  document.addEventListener("fullscreenchange", () => { if (!document.fullscreenElement) document.body.classList.remove("screen-mode"); });
}

async function loadAll() {
  await Promise.all([loadCatalog(), loadOverview(), loadHealthBadge()]);
}

bindEvents();
updateClock(); setInterval(updateClock, 1000);
loadAll().catch((error) => toast(`初始化失败：${error.message}`, "error"));
setInterval(() => { if (!document.hidden) { loadOverview().catch(() => {}); if ($("#view-feed").classList.contains("active")) loadFeed().catch(() => {}); } }, 20000);
