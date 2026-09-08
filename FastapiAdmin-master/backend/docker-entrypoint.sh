#!/bin/sh
# 后端容器启动入口：等 MySQL 端口就绪 → 执行 alembic 迁移 → 启动服务
set -e

DB_HOST="${DATABASE_HOST:-mysql}"
DB_PORT="${DATABASE_PORT:-3306}"

echo "⏳ 等待 MySQL (${DB_HOST}:${DB_PORT}) 就绪..."
until python - <<'PY'
import socket, os, sys
host = os.environ.get("DATABASE_HOST", "mysql")
port = int(os.environ.get("DATABASE_PORT", "3306"))
try:
    with socket.create_connection((host, port), timeout=3):
        pass
except Exception:
    sys.exit(1)
PY
do
  echo "  MySQL 未就绪，3 秒后重试..."
  sleep 3
done
echo "✅ MySQL 就绪"

echo "🚀 执行数据库迁移 (alembic upgrade --env=prod)..."
python main.py upgrade --env=prod

echo "▶️  启动后端服务 (uvicorn :${SERVER_PORT:-8001})..."
exec python main.py run --env=prod
