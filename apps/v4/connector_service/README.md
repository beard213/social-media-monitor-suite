# 抖音 / 快手授权连接器

该服务把平台官方或正式授权的数据接口转换为任务中心统一协议。真实凭证只能配置在连接器服务中，不放前端。

启动抖音连接器：

```bash
CONNECTOR_PLATFORM=douyin \
CONNECTOR_INTERNAL_TOKEN=change-me \
uvicorn connector_service.main:app --host 0.0.0.0 --port 9001
```

启动快手连接器：

```bash
CONNECTOR_PLATFORM=kuaishou \
CONNECTOR_INTERNAL_TOKEN=change-me \
uvicorn connector_service.main:app --host 0.0.0.0 --port 9002
```

需要实现的接口：

```text
GET  /health
POST /v1/search
POST /v1/comments
POST /v1/relations
POST /v1/media/resolve
```

代码位置：

```text
connector_service/drivers/douyin.py
connector_service/drivers/kuaishou.py
```

详细数据结构见：

```text
docs/赵帅接口填写清单.md
```
