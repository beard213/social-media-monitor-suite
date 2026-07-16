# v4.0 验证报告

验证日期：2026-07-15

## 自动检查

- Python `compileall`：通过；
- 前端 JavaScript `node --check`：通过；
- FastAPI任务中心路由加载：通过；
- 抖音、快手连接器服务模块加载：通过；
- SQLite测试数据库初始化：通过；
- `pytest`：12项通过。

## 已验证的关键链路

### 关键词任务

- 创建包含平台、关键词、排除词、区域、时间范围和内容类型的监测任务；
- 调用统一连接器 `/v1/search`；
- 搜索结果统一入库并排队评论、关系扩列、检测和推送任务；
- 真实接口未实现时返回明确的HTTP 501，不伪造平台数据。

### 直播ID任务

- `POST /api/live-monitor/start` 可按平台和直播间ID建立监控会话；
- 可直接使用前端提供的测试流地址；
- 可调用现有直播服务桥接 `/v1/live/resolve`；
- 可回退到平台连接器 `/v1/media/resolve`；
- 没有流地址时正确进入 `waiting_source`；
- 有流地址时进入 `running` 并可创建FFmpeg采集任务。

### 评论与公开关系扩列

- 评论接口 `/v1/comments` 数据结构和日期字段校验通过；
- 公开关系接口 `/v1/relations` 结构校验通过；
- 评论主题线索与公开关系线索可同时保存，不互相覆盖；
- 内容详情与AI研判页面可显示扩列线索。

### 前端与大屏

- 默认启用亮蓝科技主题；
- 支持主题切换和浏览器全屏；
- 支持1920×1080、2K及更宽屏幕的弹性布局；
- “搜索与直播接入”同时提供关键词任务和直播ID表单；
- 系统设置页显示赵帅需要填写的四类接口及直播桥接配置。

## 已验证API

- `GET /api/health`；
- `GET /api/console/overview`；
- `GET /api/console/feed`；
- `GET /api/console/risk-accounts`；
- `GET /api/console/topics`；
- `GET /api/console/connector-contract`；
- `POST /api/live-monitor/start`；
- `POST /api/contents/{content_id}/comments/fetch`；
- `POST /api/contents/{content_id}/relations/fetch`；
- 任务创建、执行、启停和删除；
- 内容检测、媒体采集、人工复核和推送入队；
- Provider搜索、评论和直播互动主动接入。

## 尚未声称通过的部分

以下依赖外部资源，测试环境没有真实凭证，因此没有伪造验证结论：

- 抖音真实全站关键词搜索；
- 快手真实全站关键词搜索；
- 平台真实评论、关注/朋友关系和短视频媒体地址；
- 真实直播间ID解析出的可持续直播流；
- 赵帅项目方正式接收地址；
- 正式文本、音频和视频检测模型准确率。
