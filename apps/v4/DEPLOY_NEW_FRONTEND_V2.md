# 新治理前端整合版部署说明

## 方式一：在现有服务器项目中覆盖前端

先备份：

```bash
cd /data4/home/minghuazhao/social-media-monitor-trace-system-v4
cp -a web web.backup_before_governance_v2
cp app/api/routes.py app/api/routes.py.backup_before_governance_v2
```

把补丁包中的以下内容覆盖到项目：

```text
web/index.html
web/static/assets/
app/api/routes.py
frontend/
FUNCTION_MIGRATION_V2.md
```

生产运行不需要安装Node，因为 `web/static/assets` 已经构建完成。

重启API：

```bash
cd /data4/home/minghuazhao/social-media-monitor-trace-system-v4
source .venv/bin/activate
pkill -f "uvicorn app.main:app" || true
nohup uvicorn app.main:app --host 0.0.0.0 --port 19001 \
  > run_logs/v4_api.log 2>&1 &
```

重启Worker：

```bash
pkill -f "python.*app.worker" || true
nohup python -m app.worker > run_logs/v4_worker.log 2>&1 &
```

访问地址：

```text
http://服务器IP:19001/
```

## 方式二：使用完整项目包

```bash
unzip ai-safety-governance-integrated-v2.zip
cd ai-safety-governance-integrated-v2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.init_db
uvicorn app.main:app --host 0.0.0.0 --port 19001
```

另开终端运行Worker：

```bash
source .venv/bin/activate
python -m app.worker
```

## 继续修改React前端

只有继续开发界面时才需要Node：

```bash
cd frontend
npm install
npm run dev
```

完成后重新构建：

```bash
npm run build
cp dist/index.html ../web/index.html
rm -rf ../web/static/assets
mkdir -p ../web/static/assets
cp -a dist/assets/. ../web/static/assets/
```

## 当前能力说明

- 视频、音频、ASR转写和证据文件使用真实数据库和服务器文件。
- 检测服务未启用时，页面如实显示“未启用/跳过”。
- 直播弹幕接口未接入时，不显示模拟弹幕。
- 抖音和快手搜索、评论、关系能力依赖授权连接器。
