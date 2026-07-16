# 前端流程优化版 V3 部署说明

## 一、适用项目目录

```text
/data4/home/minghuazhao/social-media-monitor-trace-system-v4
```

## 二、推荐方式：运行补丁脚本

将补丁包上传到：

```text
/data4/home/minghuazhao/frontend-flow-optimization-v3-patch.zip
```

解压：

```bash
cd /data4/home/minghuazhao
rm -rf /tmp/frontend-flow-optimization-v3-patch
unzip -o frontend-flow-optimization-v3-patch.zip -d /tmp
```

执行：

```bash
bash /tmp/frontend-flow-optimization-v3-patch/apply_patch.sh \
  /data4/home/minghuazhao/social-media-monitor-trace-system-v4
```

脚本会自动：

1. 创建带时间戳的备份目录；
2. 备份当前 `web`；
3. 备份当前 `frontend/src/app/App.tsx`；
4. 覆盖生产前端；
5. 覆盖React源码；
6. 输出备份路径。

## 三、手动覆盖方式

```bash
cd /data4/home/minghuazhao/social-media-monitor-trace-system-v4

STAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "backup_frontend_v3_$STAMP"
cp -a web "backup_frontend_v3_$STAMP/web"
cp -a frontend/src/app/App.tsx "backup_frontend_v3_$STAMP/App.tsx"

PATCH=/tmp/frontend-flow-optimization-v3-patch

rm -rf web/static/assets
mkdir -p web/static/assets
cp -a "$PATCH/web/index.html" web/index.html
cp -a "$PATCH/web/static/assets/." web/static/assets/
cp -a "$PATCH/frontend/src/app/App.tsx" frontend/src/app/App.tsx
```

## 四、重启服务

```bash
cd /data4/home/minghuazhao/social-media-monitor-trace-system-v4
mkdir -p run_logs

pkill -f '[u]vicorn app.main:app' || true
pkill -f '[p]ython.*app.worker' || true

nohup .venv/bin/uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 19001 \
  > run_logs/v4_api.log 2>&1 &

echo $! > run_logs/v4_api.pid

nohup .venv/bin/python -m app.worker \
  > run_logs/v4_worker.log 2>&1 &

echo $! > run_logs/v4_worker.pid
```

## 五、验证

```bash
sleep 3

ss -lntp | grep 19001

tail -n 50 run_logs/v4_api.log
tail -n 50 run_logs/v4_worker.log

curl -sS -o /dev/null \
  -w '首页HTTP状态：%{http_code}\n' \
  http://127.0.0.1:19001/

curl -sS http://127.0.0.1:19001/api/health | python -m json.tool

curl -sS http://127.0.0.1:19001/ | grep -Eo '/static/assets/index-[^" ]+'
```

正常应看到：

```text
首页HTTP状态：200
/static/assets/index-*.js
/static/assets/index-*.css
```

浏览器访问：

```text
http://116.131.52.62:19001/
```

页面缓存未更新时按：

```text
Ctrl + F5
```

## 六、回滚

补丁脚本执行后会输出备份目录，例如：

```text
/data4/home/minghuazhao/social-media-monitor-trace-system-v4/backup_frontend_v3_20260715_203000
```

回滚：

```bash
cd /data4/home/minghuazhao/social-media-monitor-trace-system-v4

rm -rf web
cp -a backup_frontend_v3_时间戳/web web
cp -a backup_frontend_v3_时间戳/App.tsx frontend/src/app/App.tsx
```

然后重新启动API和Worker。

## 七、说明

生产环境不需要运行 `npm install` 或 `npm run build`。补丁中已经包含构建后的静态文件。
