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
