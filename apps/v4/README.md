# 社交媒体及网络直播监测与溯源系统 v4.0

面向抖音、快手公开视频和网络直播的任务配置、区域筛选、评论/弹幕聚合、公开关系扩列、多模态检测、人工复核、证据保存与下游推送系统。

> 当前版本的短视频搜索、平台评论、公开账号关系和媒体解析接口已全部预留，等待赵帅或获得平台授权的项目方填写。直播监控支持输入平台和直播间ID，可接入已有直播服务，也可使用测试流先跑通分片、转写和检测链路。

## 主要页面

- 态势总览大屏
- 评论弹幕实时监控
- 风险账号处置
- AI智能研判
- 话题溯源分析
- 搜索与直播接入
- 内容发现与筛选
- 后台任务队列
- 接口与系统配置

默认采用更亮的蓝色科技风，并提供“大屏模式”。

## 快速启动

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./start-dev.sh
```

另开终端：

```bash
source .venv/bin/activate
./start-worker.sh
```

访问：

```text
http://服务器IP:18101
http://服务器IP:18101/docs
```

## 两条使用链路

### 1. 关键词搜索任务

```text
选择抖音/快手
→ 配置关键词、区域、内容类型
→ 调用平台连接器 /v1/search
→ 评论采集 /v1/comments
→ 公开关系扩列 /v1/relations
→ 检测、复核和推送
```

没有真实接口时，可以用 `demo` 平台验证全部任务流程。

### 2. 直播ID监控

```text
搜索与直播接入
→ 输入平台和直播间ID
→ 现有直播服务桥接或 /v1/media/resolve
→ FFmpeg分片
→ FunASR
→ 多模态检测
→ 证据保存
→ 推送给赵帅项目方
```

接口未返回直播流时，会进入 `waiting_source`，不会反复产生失败录制任务。

## 赵帅需要填写的位置

```text
connector_service/drivers/douyin.py
connector_service/drivers/kuaishou.py
```

方法：

```python
search()
comments()
relations()
resolve_media()
```

详细协议：

```text
docs/赵帅接口填写清单.md
docs/直播ID接入协议.md
docs/赵帅推送接口.md
```

## 关键环境变量

```env
DOUYIN_CONNECTOR_URL=
DOUYIN_CONNECTOR_TOKEN=
KUAISHOU_CONNECTOR_URL=
KUAISHOU_CONNECTOR_TOKEN=

LIVE_MONITOR_BRIDGE_URL=
LIVE_MONITOR_BRIDGE_TOKEN=

PUSH_ENABLED=false
PUSH_TARGET_NAME=赵帅项目方
PUSH_EVENTS_URL=
PUSH_MEDIA_URL=
PUSH_BEARER_TOKEN=
```

## 数据边界

系统只处理公开或正式授权获得的内容与关系线索。账号汇总使用匿名别名，不自动推断现实身份、政治属性或其他敏感个人属性；风险评分只用于人工复核排序，不执行平台封禁或自动处罚。

## 测试

```bash
python -m compileall -q app connector_service
node --check web/static/app.js
pytest -q
```
