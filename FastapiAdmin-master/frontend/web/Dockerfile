# ---- 构建阶段 ----
FROM node:22-alpine AS builder
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install
COPY . .
# 生产构建：build:prod = vite build --mode production（跳过 vue-tsc，加载 .env.production）
RUN NODE_OPTIONS=--max-old-space-size=2048 pnpm run build:prod

# ---- 运行阶段 ----
FROM nginx:alpine
# 构建产物 base=/web，落在 dist/ 下；拷到 html/web，使 /web/... 可访问
COPY --from=builder /app/dist /usr/share/nginx/html/web
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
