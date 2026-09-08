# 后端 API 镜像（python:3.12-slim）
FROM python:3.12-slim

# 不缓冲 Python 输出 / 不写 .pyc / pip 不缓存，便于看日志、减小层
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 极少量编译依赖：覆盖个别可能无 linux wheel 的传递依赖（pure-python 包多数用不到）
# 腾讯云机器加速：构建前把 Debian 源换成腾讯云镜像（registry-mirrors 只管 docker 镜像拉取，管不到 apt/pip）
RUN sed -i 's|deb.debian.org|mirrors.tencent.com|g' /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources 2>/dev/null || true
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖（利用 Docker 层缓存：依赖不变就不重装）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.tencent.com/pypi/simple/

# 复制后端源码
COPY . .

# 防止 init_app.register_frontend 把不存在的 dist 挂成 /web 导致启动崩溃（nginx 会抢先接管 /web）
RUN mkdir -p /app/dist /app/static

# 入口：等 MySQL → alembic 自动迁移 → 启动 uvicorn
RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]
