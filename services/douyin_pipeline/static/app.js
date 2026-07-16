async function api(url, options = {}) {
    const res = await fetch(url, options);
    return await res.json();
}

function safe(v) {
    if (v === null || v === undefined || v === "") return "-";
    return String(v);
}

async function loadProcesses() {
    const data = await api("/api/processes");

    const monitor = document.getElementById("monitorStatus");
    const pipeline = document.getElementById("pipelineStatus");

    if (data.monitor && data.monitor.running) {
        monitor.innerText = "运行中，PID=" + data.monitor.pid;
        monitor.className = "status-running";
    } else {
        monitor.innerText = "未运行";
        monitor.className = "status-stop";
    }

    if (data.pipeline && data.pipeline.running) {
        pipeline.innerText = "运行中，PID=" + data.pipeline.pid;
        pipeline.className = "status-running";
    } else {
        pipeline.innerText = "未运行";
        pipeline.className = "status-stop";
    }
}

async function loadUsers() {
    const users = await api("/api/users");
    const body = document.getElementById("usersBody");

    let html = "";

    users.forEach(u => {
        const status = u.status === "直播中"
            ? "<span class='badge-live'>直播中</span>"
            : "<span class='badge-off'>" + safe(u.status) + "</span>";

        html += `
            <tr>
                <td>${safe(u.name)}</td>
                <td>${safe(u.uid)}</td>
                <td>${u.enable ? "启用" : "停用"}</td>
                <td>${status}</td>
                <td>${safe(u.room_id)}</td>
                <td>${safe(u.last_check)}</td>
                <td>
                    <button class="small-btn gray" onclick="toggleUser('${u.uid}')">
                        ${u.enable ? "停用" : "启用"}
                    </button>
                    <button class="small-btn red" onclick="deleteUser('${u.uid}')">
                        删除
                    </button>
                </td>
            </tr>
        `;
    });

    if (!html) {
        html = "<tr><td colspan='7'>暂无主播任务</td></tr>";
    }

    body.innerHTML = html;
}

async function addUser() {
    const name = document.getElementById("name").value.trim();
    const uid = document.getElementById("uid").value.trim();
    const mockRoomId = document.getElementById("mockRoomId").value.trim();

    if (!name || !uid) {
        alert("主播名称和 UID 不能为空");
        return;
    }

    const url =
        "/api/users/add?name=" + encodeURIComponent(name) +
        "&uid=" + encodeURIComponent(uid) +
        "&mock_room_id=" + encodeURIComponent(mockRoomId);

    const data = await api(url, { method: "POST" });
    alert(data.message || "完成");

    document.getElementById("name").value = "";
    document.getElementById("uid").value = "";
    document.getElementById("mockRoomId").value = "";

    loadAll();
}

async function deleteUser(uid) {
    if (!confirm("确定删除该主播任务吗？")) return;

    const data = await api("/api/users/" + encodeURIComponent(uid), {
        method: "DELETE"
    });

    alert(data.message || "已删除");
    loadAll();
}

async function toggleUser(uid) {
    const data = await api("/api/users/" + encodeURIComponent(uid) + "/toggle", {
        method: "POST"
    });

    alert(data.message || "完成");
    loadAll();
}

async function loadSources() {
    const sources = await api("/api/live-sources");

    let text = "";

    sources.forEach((s, idx) => {
        text += (idx + 1) + ". " + s.name + " = " + s.url + "\n";
    });

    if (!text) {
        text = "暂无采集源。";
    }

    document.getElementById("sourceList").innerText = text;
}

async function loadOutputStats() {
    const stats = await api("/api/output-stats");

    let text = "";

    stats.forEach(s => {
        text += "[" + s.account + "]\n";
        text += "video:    " + s.video_count + "\n";
        text += "audio:    " + s.audio_count + "\n";
        text += "text:     " + s.text_count + "\n";
        text += "metadata: " + s.metadata_count + "\n";
        text += "audit:    " + s.audit_count + "\n";
        text += "latest:   " + (s.latest_text || "-") + "\n\n";
    });

    if (!text) {
        text = "暂无 output 结果。";
    }

    document.getElementById("outputStats").innerText = text;
}

async function startMonitor() {
    const data = await api("/api/processes/monitor/start", {
        method: "POST"
    });

    alert(data.message || "完成");
    loadAll();
}

async function stopMonitor() {
    const data = await api("/api/processes/monitor/stop", {
        method: "POST"
    });

    alert(data.message || "完成");
    loadAll();
}

async function startPipeline() {
    const maxRounds = document.getElementById("maxRounds").value.trim() || "0";
    const maxWorkers = document.getElementById("maxWorkers").value.trim() || "2";
    const cleanOutput = document.getElementById("cleanOutput").checked;
    const cleanLogs = document.getElementById("cleanLogs").checked;

    const url =
        "/api/processes/pipeline/start?max_rounds=" + encodeURIComponent(maxRounds) +
        "&max_workers=" + encodeURIComponent(maxWorkers) +
        "&clean_output=" + cleanOutput +
        "&clean_logs=" + cleanLogs;

    const data = await api(url, { method: "POST" });

    alert(data.message || "完成");
    loadAll();
}

async function stopPipeline() {
    const data = await api("/api/processes/pipeline/stop", {
        method: "POST"
    });

    alert(data.message || "完成");
    loadAll();
}

async function loadLog(name) {
    const data = await api("/api/logs/" + name);
    document.getElementById("logBox").innerText = data.content || "暂无日志";
}

async function loadAll() {
    await loadProcesses();
    await loadUsers();
    await loadSources();
    await loadOutputStats();
}

loadAll();
setInterval(loadAll, 10000);


// ==================== Audit Frontend Extension ====================

async function loadAuditStatus() {
    const box = document.getElementById("auditStatus");
    if (!box) return;

    try {
        const data = await api("/api/processes/audit/status");

        if (data.running) {
            box.innerText = "运行中，PID=" + data.pid;
            box.className = "status-running";
        } else {
            box.innerText = "未运行";
            box.className = "status-stop";
        }
    } catch (e) {
        box.innerText = "状态获取失败";
        box.className = "status-stop";
    }
}


async function startAudit() {
    const data = await api("/api/processes/audit/start?interval=30", {
        method: "POST"
    });

    alert(data.message || "检测任务已启动");
    loadAll();
}


async function stopAudit() {
    const data = await api("/api/processes/audit/stop", {
        method: "POST"
    });

    alert(data.message || "检测任务已停止");
    loadAll();
}


async function startFull() {
    const maxRounds = document.getElementById("maxRounds").value.trim() || "0";
    const maxWorkers = document.getElementById("maxWorkers").value.trim() || "2";
    const cleanOutput = document.getElementById("cleanOutput").checked;
    const cleanLogs = document.getElementById("cleanLogs").checked;

    const url =
        "/api/processes/full/start?max_rounds=" + encodeURIComponent(maxRounds) +
        "&max_workers=" + encodeURIComponent(maxWorkers) +
        "&clean_output=" + cleanOutput +
        "&clean_logs=" + cleanLogs;

    const data = await api(url, { method: "POST" });

    alert(data.message || "完整流程已启动");
    loadAll();
    loadAuditResults();
}


async function stopFull() {
    const data = await api("/api/processes/full/stop", {
        method: "POST"
    });

    alert(data.message || "完整流程已停止");
    loadAll();
    loadAuditResults();
}


async function loadAuditResults() {
    const box = document.getElementById("auditResults");
    if (!box) return;

    const data = await api("/api/audit-results");

    let text = "";

    data.forEach(item => {
        text += "[" + item.account + "] ";
        text += item.segment_id + " => ";
        text += item.status + "\n";

        if (item.labels && item.labels.length) {
            text += "labels: " + item.labels.join(", ") + "\n";
        }

        if (item.risk_words && item.risk_words.length) {
            text += "risk_words: " + item.risk_words.join(", ") + "\n";
        }

        text += "type: " + (item.audit_type || "-") + "\n";
        text += "time: " + (item.audit_time || "-") + "\n";
        text += "file: " + item.file + "\n\n";
    });

    if (!text) {
        text = "暂无检测结果";
    }

    box.innerText = text;
}


async function loadAuditLog() {
    const box = document.getElementById("auditResults");
    if (!box) return;

    const data = await api("/api/audit-log");
    box.innerText = data.content || "暂无检测日志";
}


// 覆盖原 loadAll，增加检测状态和检测结果刷新
async function loadAll() {
    await loadProcesses();
    await loadAuditStatus();
    await loadUsers();
    await loadSources();
    await loadOutputStats();
    await loadAuditResults();
}

setInterval(loadAuditResults, 10000);
setInterval(loadAuditStatus, 10000);


// ==================== Multi-modal audit result frontend ====================

async function loadAuditResults() {
    const box = document.getElementById("auditResults");
    if (!box) return;

    let data = [];

    try {
        data = await api("/api/audit-all-results");
    } catch (e) {
        box.innerText = "检测结果加载失败：" + e;
        return;
    }

    let text = "";

    data.forEach(item => {
        text += "直播源: " + (item.account || "-") + "\n";
        text += "片段: " + (item.segment_id || "-") + "\n";
        text += "综合结果: " + (item.status || "未知") + "\n";
        text += "视频检测: " + (item.video_status || "未知") + "\n";
        text += "音频检测: " + (item.audio_status || "未知") + "\n";
        text += "文本检测: " + (item.text_status || "未知") + "\n";

        if (item.labels && item.labels.length) {
            text += "风险标签: " + item.labels.join(", ") + "\n";
        }

        if (item.risk_words && item.risk_words.length) {
            text += "风险词: " + item.risk_words.join(", ") + "\n";
        }

        if (item.max_confidence !== null && item.max_confidence !== undefined) {
            text += "最高置信度: " + item.max_confidence + "\n";
        }

        text += "检测时间: " + (item.audit_time || "-") + "\n";
        text += "结果文件: " + (item.file || "-") + "\n";
        text += "\n----------------------------------------\n\n";
    });

    if (!text) {
        text = "暂无检测结果。请先启动完整流程，并等待 2 到 4 分钟。";
    }

    box.innerText = text;
}


// ===== 三路检测结果展示：视频 + 音频 + 文本 =====
async function loadAuditResults() {
    const box = document.getElementById("auditResults");
    if (!box) return;

    let data = [];

    try {
        data = await api("/api/audit-all-results");
    } catch (e) {
        box.innerText = "检测结果加载失败，请确认后端是否存在 /api/audit-all-results 接口。";
        return;
    }

    if (!data || data.length === 0) {
        box.innerText = "暂无检测结果。请先点击“启动完整流程”，并等待 2 到 5 分钟。";
        return;
    }

    let text = "";

    data.forEach((item, idx) => {
        let seg = item.segment_id || "-";
        seg = seg.replace(".all.audit.json", "").replace(".audit.json", "");

        text += "第 " + (idx + 1) + " 条检测结果\n";
        text += "直播源：" + (item.account || "-") + "\n";
        text += "片段编号：" + seg + "\n";
        text += "综合结果：" + (item.status || "未知") + "\n";
        text += "视频检测：" + (item.video_status || "未知") + "\n";
        text += "音频检测：" + (item.audio_status || "未知") + "\n";
        text += "文本检测：" + (item.text_status || "未知") + "\n";

        if (item.labels && item.labels.length > 0) {
            text += "风险标签：" + item.labels.join("、") + "\n";
        }

        if (item.risk_words && item.risk_words.length > 0) {
            text += "风险词：" + item.risk_words.join("、") + "\n";
        }

        text += "检测时间：" + (item.audit_time || "-") + "\n";
        text += "\n----------------------------------------\n\n";
    });

    box.innerText = text;
}


// ===== 三路检测结果展示：视频 + 音频 + 文本 =====
async function loadAuditResults() {
    const box = document.getElementById("auditResults");
    if (!box) return;

    let data = [];

    try {
        data = await api("/api/audit-all-results");
    } catch (e) {
        box.innerText = "检测结果加载失败，请确认后端是否存在 /api/audit-all-results 接口。";
        return;
    }

    if (!data || data.length === 0) {
        box.innerText = "暂无检测结果。请先点击“启动完整流程”，并等待 2 到 5 分钟。";
        return;
    }

    let text = "";

    data.forEach((item, idx) => {
        let seg = item.segment_id || "-";
        seg = seg.replace(".all.audit.json", "").replace(".audit.json", "");

        text += "第 " + (idx + 1) + " 条检测结果\n";
        text += "直播源：" + (item.account || "-") + "\n";
        text += "片段编号：" + seg + "\n";
        text += "综合结果：" + (item.status || "未知") + "\n";
        text += "视频检测：" + (item.video_status || "未知") + "\n";
        text += "音频检测：" + (item.audio_status || "未知") + "\n";
        text += "文本检测：" + (item.text_status || "未知") + "\n";

        if (item.labels && item.labels.length > 0) {
            text += "风险标签：" + item.labels.join("、") + "\n";
        }

        if (item.risk_words && item.risk_words.length > 0) {
            text += "风险词：" + item.risk_words.join("、") + "\n";
        }

        text += "检测时间：" + (item.audit_time || "-") + "\n";
        text += "\n----------------------------------------\n\n";
    });

    box.innerText = text;
}


// ===== 三路检测结果展示：视频 + 音频 + 文本 =====
async function loadAuditResults() {
    const box = document.getElementById("auditResults");
    if (!box) return;

    let data = [];

    try {
        data = await api("/api/audit-all-results");
    } catch (e) {
        box.innerText = "检测结果加载失败，请确认后端是否存在 /api/audit-all-results 接口。";
        return;
    }

    if (!data || data.length === 0) {
        box.innerText = "暂无检测结果。请先点击“启动完整流程”，并等待 2 到 5 分钟。";
        return;
    }

    let text = "";

    data.forEach((item, idx) => {
        let seg = item.segment_id || "-";
        seg = seg.replace(".all.audit.json", "").replace(".audit.json", "");

        text += "第 " + (idx + 1) + " 条检测结果\n";
        text += "直播源：" + (item.account || "-") + "\n";
        text += "片段编号：" + seg + "\n";
        text += "综合结果：" + (item.status || "未知") + "\n";
        text += "视频检测：" + (item.video_status || "未知") + "\n";
        text += "音频检测：" + (item.audio_status || "未知") + "\n";
        text += "文本检测：" + (item.text_status || "未知") + "\n";

        if (item.labels && item.labels.length > 0) {
            text += "风险标签：" + item.labels.join("、") + "\n";
        }

        if (item.risk_words && item.risk_words.length > 0) {
            text += "风险词：" + item.risk_words.join("、") + "\n";
        }

        text += "检测时间：" + (item.audit_time || "-") + "\n";
        text += "\n----------------------------------------\n\n";
    });

    box.innerText = text;
}
JScat >> static/app.js <<'JS'


// ===== 三路检测结果展示：视频 + 音频 + 文本 =====
async function loadAuditResults() {
    const box = document.getElementById("auditResults");
    if (!box) return;

    let data = [];

    try {
        data = await api("/api/audit-all-results");
    } catch (e) {
        box.innerText = "检测结果加载失败，请确认后端是否存在 /api/audit-all-results 接口。";
        return;
    }

    if (!data || data.length === 0) {
        box.innerText = "暂无检测结果。请先点击“启动完整流程”，并等待 2 到 5 分钟。";
        return;
    }

    let text = "";

    data.forEach((item, idx) => {
        let seg = item.segment_id || "-";
        seg = seg.replace(".all.audit.json", "").replace(".audit.json", "");

        text += "第 " + (idx + 1) + " 条检测结果\n";
        text += "直播源：" + (item.account || "-") + "\n";
        text += "片段编号：" + seg + "\n";
        text += "综合结果：" + (item.status || "未知") + "\n";
        text += "视频检测：" + (item.video_status || "未知") + "\n";
        text += "音频检测：" + (item.audio_status || "未知") + "\n";
        text += "文本检测：" + (item.text_status || "未知") + "\n";

        if (item.labels && item.labels.length > 0) {
            text += "风险标签：" + item.labels.join("、") + "\n";
        }

        if (item.risk_words && item.risk_words.length > 0) {
            text += "风险词：" + item.risk_words.join("、") + "\n";
        }

        text += "检测时间：" + (item.audit_time || "-") + "\n";
        text += "\n----------------------------------------\n\n";
    });

    box.innerText = text;
}
JScat >> static/app.js <<'JS'


// ===== 三路检测结果展示：视频 + 音频 + 文本 =====
async function loadAuditResults() {
    const box = document.getElementById("auditResults");
    if (!box) return;

    let data = [];

    try {
        data = await api("/api/audit-all-results");
    } catch (e) {
        box.innerText = "检测结果加载失败，请确认后端是否存在 /api/audit-all-results 接口。";
        return;
    }

    if (!data || data.length === 0) {
        box.innerText = "暂无检测结果。请先点击“启动完整流程”，并等待 2 到 5 分钟。";
        return;
    }

    let text = "";

    data.forEach((item, idx) => {
        let seg = item.segment_id || "-";
        seg = seg.replace(".all.audit.json", "").replace(".audit.json", "");

        text += "第 " + (idx + 1) + " 条检测结果\n";
        text += "直播源：" + (item.account || "-") + "\n";
        text += "片段编号：" + seg + "\n";
        text += "综合结果：" + (item.status || "未知") + "\n";
        text += "视频检测：" + (item.video_status || "未知") + "\n";
        text += "音频检测：" + (item.audio_status || "未知") + "\n";
        text += "文本检测：" + (item.text_status || "未知") + "\n";

        if (item.labels && item.labels.length > 0) {
            text += "风险标签：" + item.labels.join("、") + "\n";
        }

        if (item.risk_words && item.risk_words.length > 0) {
            text += "风险词：" + item.risk_words.join("、") + "\n";
        }

        text += "检测时间：" + (item.audit_time || "-") + "\n";
        text += "\n----------------------------------------\n\n";
    });

    box.innerText = text;
}
JScat >> static/app.js <<'JS'


// ===== 三路检测结果展示：视频 + 音频 + 文本 =====
async function loadAuditResults() {
    const box = document.getElementById("auditResults");
    if (!box) return;

    let data = [];

    try {
        data = await api("/api/audit-all-results");
    } catch (e) {
        box.innerText = "检测结果加载失败，请确认后端是否存在 /api/audit-all-results 接口。";
        return;
    }

    if (!data || data.length === 0) {
        box.innerText = "暂无检测结果。请先点击“启动完整流程”，并等待 2 到 5 分钟。";
        return;
    }

    let text = "";

    data.forEach((item, idx) => {
        let seg = item.segment_id || "-";
        seg = seg.replace(".all.audit.json", "").replace(".audit.json", "");

        text += "第 " + (idx + 1) + " 条检测结果\n";
        text += "直播源：" + (item.account || "-") + "\n";
        text += "片段编号：" + seg + "\n";
        text += "综合结果：" + (item.status || "未知") + "\n";
        text += "视频检测：" + (item.video_status || "未知") + "\n";
        text += "音频检测：" + (item.audio_status || "未知") + "\n";
        text += "文本检测：" + (item.text_status || "未知") + "\n";

        if (item.labels && item.labels.length > 0) {
            text += "风险标签：" + item.labels.join("、") + "\n";
        }

        if (item.risk_words && item.risk_words.length > 0) {
            text += "风险词：" + item.risk_words.join("、") + "\n";
        }

        text += "检测时间：" + (item.audit_time || "-") + "\n";
        text += "\n----------------------------------------\n\n";
    });

    box.innerText = text;
}
JScat >> static/app.js <<'JS'


// ===== 三路检测结果展示：视频 + 音频 + 文本 =====
async function loadAuditResults() {
    const box = document.getElementById("auditResults");
    if (!box) return;

    let data = [];

    try {
        data = await api("/api/audit-all-results");
    } catch (e) {
        box.innerText = "检测结果加载失败，请确认后端是否存在 /api/audit-all-results 接口。";
        return;
    }

    if (!data || data.length === 0) {
        box.innerText = "暂无检测结果。请先点击“启动完整流程”，并等待 2 到 5 分钟。";
        return;
    }

    let text = "";

    data.forEach((item, idx) => {
        let seg = item.segment_id || "-";
        seg = seg.replace(".all.audit.json", "").replace(".audit.json", "");

        text += "第 " + (idx + 1) + " 条检测结果\n";
        text += "直播源：" + (item.account || "-") + "\n";
        text += "片段编号：" + seg + "\n";
        text += "综合结果：" + (item.status || "未知") + "\n";
        text += "视频检测：" + (item.video_status || "未知") + "\n";
        text += "音频检测：" + (item.audio_status || "未知") + "\n";
        text += "文本检测：" + (item.text_status || "未知") + "\n";

        if (item.labels && item.labels.length > 0) {
            text += "风险标签：" + item.labels.join("、") + "\n";
        }

        if (item.risk_words && item.risk_words.length > 0) {
            text += "风险词：" + item.risk_words.join("、") + "\n";
        }

        text += "检测时间：" + (item.audit_time || "-") + "\n";
        text += "\n----------------------------------------\n\n";
    });

    box.innerText = text;
}
JScat >> static/app.js <<'JS'


// ===== 三路检测结果展示：视频 + 音频 + 文本 =====
async function loadAuditResults() {
    const box = document.getElementById("auditResults");
    if (!box) return;

    let data = [];

    try {
        data = await api("/api/audit-all-results");
    } catch (e) {
        box.innerText = "检测结果加载失败，请确认后端是否存在 /api/audit-all-results 接口。";
        return;
    }

    if (!data || data.length === 0) {
        box.innerText = "暂无检测结果。请先点击“启动完整流程”，并等待 2 到 5 分钟。";
        return;
    }

    let text = "";

    data.forEach((item, idx) => {
        let seg = item.segment_id || "-";
        seg = seg.replace(".all.audit.json", "").replace(".audit.json", "");

        text += "第 " + (idx + 1) + " 条检测结果\n";
        text += "直播源：" + (item.account || "-") + "\n";
        text += "片段编号：" + seg + "\n";
        text += "综合结果：" + (item.status || "未知") + "\n";
        text += "视频检测：" + (item.video_status || "未知") + "\n";
        text += "音频检测：" + (item.audio_status || "未知") + "\n";
        text += "文本检测：" + (item.text_status || "未知") + "\n";

        if (item.labels && item.labels.length > 0) {
            text += "风险标签：" + item.labels.join("、") + "\n";
        }

        if (item.risk_words && item.risk_words.length > 0) {
            text += "风险词：" + item.risk_words.join("、") + "\n";
        }

        text += "检测时间：" + (item.audit_time || "-") + "\n";
        text += "\n----------------------------------------\n\n";
    });

    box.innerText = text;
}
JScat >> static/app.js <<'JS'


// ===== 三路检测结果展示：视频 + 音频 + 文本 =====
async function loadAuditResults() {
    const box = document.getElementById("auditResults");
    if (!box) return;

    let data = [];

    try {
        data = await api("/api/audit-all-results");
    } catch (e) {
        box.innerText = "检测结果加载失败，请确认后端是否存在 /api/audit-all-results 接口。";
        return;
    }

    if (!data || data.length === 0) {
        box.innerText = "暂无检测结果。请先点击“启动完整流程”，并等待 2 到 5 分钟。";
        return;
    }

    let text = "";

    data.forEach((item, idx) => {
        let seg = item.segment_id || "-";
        seg = seg.replace(".all.audit.json", "").replace(".audit.json", "");

        text += "第 " + (idx + 1) + " 条检测结果\n";
        text += "直播源：" + (item.account || "-") + "\n";
        text += "片段编号：" + seg + "\n";
        text += "综合结果：" + (item.status || "未知") + "\n";
        text += "视频检测：" + (item.video_status || "未知") + "\n";
        text += "音频检测：" + (item.audio_status || "未知") + "\n";
        text += "文本检测：" + (item.text_status || "未知") + "\n";

        if (item.labels && item.labels.length > 0) {
            text += "风险标签：" + item.labels.join("、") + "\n";
        }

        if (item.risk_words && item.risk_words.length > 0) {
            text += "风险词：" + item.risk_words.join("、") + "\n";
        }

        text += "检测时间：" + (item.audit_time || "-") + "\n";
        text += "\n----------------------------------------\n\n";
    });

    box.innerText = text;
}
JSssssadadwqdqcat >> static/app.js <<'JS'


// ===== 三路检测结果展示：视频 + 音频 + 文本 =====
async function loadAuditResults() {
    const box = document.getElementById("auditResults");
    if (!box) return;

    let data = [];

    try {
        data = await api("/api/audit-all-results");
    } catch (e) {
        box.innerText = "检测结果加载失败，请确认后端是否存在 /api/audit-all-results 接口。";
        return;
    }

    if (!data || data.length === 0) {
        box.innerText = "暂无检测结果。请先点击“启动完整流程”，并等待 2 到 5 分钟。";
        return;
    }

    let text = "";

    data.forEach((item, idx) => {
        let seg = item.segment_id || "-";
        seg = seg.replace(".all.audit.json", "").replace(".audit.json", "");

        text += "第 " + (idx + 1) + " 条检测结果\n";
        text += "直播源：" + (item.account || "-") + "\n";
        text += "片段编号：" + seg + "\n";
        text += "综合结果：" + (item.status || "未知") + "\n";
        text += "视频检测：" + (item.video_status || "未知") + "\n";
        text += "音频检测：" + (item.audio_status || "未知") + "\n";
        text += "文本检测：" + (item.text_status || "未知") + "\n";

        if (item.labels && item.labels.length > 0) {
            text += "风险标签：" + item.labels.join("、") + "\n";
        }

        if (item.risk_words && item.risk_words.length > 0) {
            text += "风险词：" + item.risk_words.join("、") + "\n";
        }

        text += "检测时间：" + (item.audit_time || "-") + "\n";
        text += "\n----------------------------------------\n\n";
    });

    box.innerText = text;
}
