# 直播ID接入协议

系统已经增加“平台 + 直播间ID”接入页面和任务中心接口：

```http
POST /api/live-monitor/start
```

系统按以下优先级解析直播源：

1. 前端或调用方直接传入 `stream_url`，用于测试已有直播链路；
2. 调用已经完成的直播监控桥接服务；
3. 调用抖音/快手连接器的 `/v1/media/resolve`；
4. 都未返回直播流时，登记直播ID并置为 `waiting_source`，不会反复产生失败录制任务。

## 现有直播服务桥接

任务中心 `.env`：

```env
LIVE_MONITOR_BRIDGE_URL=http://127.0.0.1:9100
LIVE_MONITOR_BRIDGE_TOKEN=内部Token
```

现有直播服务需要提供：

```http
POST /v1/live/resolve
Authorization: Bearer <LIVE_MONITOR_BRIDGE_TOKEN>
```

请求：

```json
{
  "platform": "douyin",
  "room_id": "808207714751",
  "segment_seconds": 120,
  "keywords": ["雄安"],
  "regions": ["xiongan"]
}
```

返回：

```json
{
  "title": "直播间标题",
  "description": "",
  "source_url": "https://live.douyin.com/808207714751",
  "stream_url": "https://...",
  "cover_url": "",
  "author_id": "公开主播ID",
  "expires_at": "2026-07-15T11:00:00+08:00",
  "request_headers": {
    "User-Agent": "...",
    "Referer": "..."
  }
}
```

返回 `stream_url` 后，主系统会：

```text
建立直播会话
→ FFmpeg按60/120/300秒分片
→ 抽取音频
→ FunASR转写
→ 文本/音频/视频检测
→ 保存证据与哈希
→ 可选推送给赵帅项目方
```

## 前端测试

打开：

```text
搜索与直播接入 → 直播ID监控接入
```

填写平台、直播ID。已有可访问测试流时，可把流地址粘贴到“测试流地址”，这样不依赖平台搜索API即可测试分片与检测链路。
