from starlette.responses import Response


HOTFIX = r'''
<script id="v4-live-delete-hotfix">
(function () {
  "use strict";

  function toast(message, isError) {
    const old = document.getElementById("v4-hotfix-toast");
    if (old) old.remove();

    const node = document.createElement("div");
    node.id = "v4-hotfix-toast";
    node.textContent = (isError ? "✕ " : "✓ ") + message;

    Object.assign(node.style, {
      position: "fixed",
      top: "18px",
      left: "50%",
      transform: "translateX(-50%)",
      zIndex: "999999",
      minWidth: "360px",
      padding: "13px 18px",
      borderRadius: "8px",
      fontSize: "14px",
      boxShadow: "0 8px 30px rgba(15,42,74,.2)",
      color: isError ? "#991b1b" : "#166534",
      background: isError ? "#fef2f2" : "#f0fdf4",
      border: isError
        ? "1px solid #fca5a5"
        : "1px solid #86efac"
    });

    document.body.appendChild(node);
    setTimeout(() => node.remove(), 3500);
  }

  async function requestJson(url, options) {
    const response = await fetch(url, options || {});
    const text = await response.text();

    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch (_) {
      data = {detail: text};
    }

    if (!response.ok) {
      throw new Error(
        data.detail ||
        data.message ||
        `请求失败：HTTP ${response.status}`
      );
    }

    return data;
  }

  function getCurrentRoomId() {
    const text = document.body.innerText || "";
    const match = text.match(/房间\/内容ID\s*([0-9]+)/);
    return match ? match[1] : "";
  }

  async function findCurrentSession() {
    const roomId = getCurrentRoomId();

    if (!roomId) {
      throw new Error("请先选择左侧直播会话");
    }

    const [contents, sessions] = await Promise.all([
      requestJson(
        "/api/contents?content_type=live&limit=500"
      ),
      requestJson("/api/live-sessions")
    ]);

    const content = (contents || []).find(
      item =>
        String(item.platform_content_id) ===
        String(roomId)
    );

    if (!content) {
      throw new Error(
        `没有找到直播间 ${roomId} 的内容记录`
      );
    }

    const matches = (sessions || [])
      .filter(
        item =>
          Number(item.content_id) === Number(content.id)
      )
      .sort((a, b) => Number(b.id) - Number(a.id));

    if (!matches.length) {
      throw new Error("当前直播间没有可删除的会话");
    }

    return {
      roomId,
      content,
      session: matches[0]
    };
  }

  async function deleteCurrentSession() {
    try {
      const target = await findCurrentSession();
      const title =
        target.content.title ||
        `直播间 ${target.roomId}`;

      const confirmed = window.confirm(
        `确定删除直播监测任务“${title}”吗？\n\n` +
        "该任务将从直播会话列表中删除，" +
        "已采集的视频、转写及检测证据仍然保留。"
      );

      if (!confirmed) return;

      try {
        await requestJson(
          `/api/live-sessions/${target.session.id}/stop`,
          {method: "POST"}
        );
      } catch (_) {
        // 已停止的任务仍然可以继续删除。
      }

      await requestJson(
        `/api/live-sessions/${target.session.id}`,
        {method: "DELETE"}
      );

      toast(`直播任务“${title}”已删除`, false);

      // 不再刷新整个网页，只调用React页面已有的刷新按钮。
      setTimeout(() => {
        const refreshButton = Array.from(
          document.querySelectorAll("button")
        ).find(button => {
          return (
            button.textContent || ""
          ).trim() === "刷新";
        });

        if (refreshButton) {
          refreshButton.click();
        }

        // 等列表刷新后，自动选中剩余的第一条直播会话。
        setTimeout(() => {
          const firstSessionButton = document.querySelector(
            "button.w-full.text-left"
          );

          if (firstSessionButton) {
            firstSessionButton.click();
          }
        }, 600);
      }, 200);
    } catch (error) {
      toast(
        error && error.message
          ? error.message
          : "删除任务失败",
        true
      );
    }
  }

  function installDeleteButton() {
    const stopButton = Array.from(
      document.querySelectorAll("button")
    ).find(
      button =>
        (button.textContent || "")
          .trim()
          .includes("停止监测")
    );

    if (!stopButton) return;

    const current = document.getElementById(
      "v4-delete-live-session"
    );

    if (current && current.isConnected) return;

    const button = document.createElement("button");

    button.id = "v4-delete-live-session";
    button.type = "button";
    button.className = stopButton.className;
    button.textContent = "删除任务";

    Object.assign(button.style, {
      marginLeft: "8px",
      color: "#dc2626",
      borderColor: "#fca5a5",
      background: "#ffffff"
    });

    button.addEventListener(
      "click",
      event => {
        event.preventDefault();
        event.stopPropagation();
        deleteCurrentSession();
      }
    );

    stopButton.insertAdjacentElement(
      "afterend",
      button
    );
  }

  const nativeFetch = window.fetch.bind(window);

  window.fetch = async function () {
    const args = Array.from(arguments);
    const input = args[0];

    const url =
      typeof input === "string"
        ? input
        : input && input.url
          ? input.url
          : "";

    const response = await nativeFetch(...args);

    if (
      response.ok &&
      url.includes("/api/live-monitor/start")
    ) {
      setTimeout(
        () => toast(
          "直播间添加成功，系统已开始监控",
          false
        ),
        100
      );
    }

    return response;
  };

  function start() {
    installDeleteButton();

    new MutationObserver(
      installDeleteButton
    ).observe(
      document.body,
      {
        childList: true,
        subtree: true
      }
    );

    setInterval(installDeleteButton, 1000);
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      start
    );
  } else {
    start();
  }
})();
</script>
'''


def install_live_ui_hotfix(app):
    @app.middleware("http")
    async def inject_hotfix(request, call_next):
        response = await call_next(request)

        content_type = response.headers.get(
            "content-type",
            "",
        )

        if (
            request.method != "GET"
            or "text/html" not in content_type
        ):
            return response

        if hasattr(response, "body_iterator"):
            chunks = []

            async for chunk in response.body_iterator:
                if isinstance(chunk, bytes):
                    chunks.append(chunk)
                else:
                    chunks.append(str(chunk).encode("utf-8"))

            body = b"".join(chunks)
        else:
            body = getattr(response, "body", b"")

        html = body.decode("utf-8", errors="ignore")

        if (
            "v4-live-delete-hotfix" not in html
            and "</body>" in html
        ):
            html = html.replace(
                "</body>",
                HOTFIX + "\n</body>",
                1,
            )

        headers = dict(response.headers)
        headers.pop("content-length", None)
        headers.pop("content-encoding", None)
        headers["cache-control"] = "no-store"

        return Response(
            content=html,
            status_code=response.status_code,
            headers=headers,
            media_type="text/html",
        )
