#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-$HOME/social-media-monitor-complete}"

if [[ ! -d "$TARGET" || ! -f "$TARGET/app/main.py" ]]; then
  echo "目标目录不是现有项目：$TARGET" >&2
  echo "用法：bash tools/upgrade_existing.sh ~/social-media-monitor-complete" >&2
  exit 1
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="${TARGET%/}-backup-$STAMP"

echo "[1/5] 备份现有项目到：$BACKUP"
mkdir -p "$BACKUP"
for item in .env data app web config docs scripts tools tests README.md VERSION; do
  if [[ -e "$TARGET/$item" ]]; then cp -a "$TARGET/$item" "$BACKUP/"; fi
done

echo "[2/5] 保留 .env、.venv、data、run_logs，替换代码"
for item in app web config docs examples scripts tests tools; do
  rm -rf "$TARGET/$item"
  cp -a "$SOURCE_ROOT/$item" "$TARGET/"
done
for item in README.md VERSION PROJECT_MANIFEST.txt VALIDATION_REPORT.md requirements.txt requirements-asr.txt pyproject.toml Dockerfile docker-compose.yml docker-compose.demo.yml start-dev.sh start-worker.sh .env.example .gitignore; do
  if [[ -e "$SOURCE_ROOT/$item" ]]; then cp -a "$SOURCE_ROOT/$item" "$TARGET/$item"; fi
done
chmod +x "$TARGET/start-dev.sh" "$TARGET/start-worker.sh" "$TARGET/tools/upgrade_existing.sh"

echo "[3/5] 检查虚拟环境"
if [[ -x "$TARGET/.venv/bin/python" ]]; then
  PYTHON_BIN="$TARGET/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
  echo "未发现旧虚拟环境，将使用：$PYTHON_BIN"
fi

echo "[4/5] 初始化新表并回填旧任务配置"
cd "$TARGET"
export PYTHONPATH=.
"$PYTHON_BIN" -m app.init_db

echo "[5/5] 语法检查"
"$PYTHON_BIN" -m compileall -q app scripts examples

echo
printf '升级完成。\n项目：%s\n备份：%s\n' "$TARGET" "$BACKUP"
echo "请重新启动 ./start-dev.sh 和 ./start-worker.sh"
