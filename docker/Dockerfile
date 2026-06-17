FROM node:22.19.0-alpine as build-stage
LABEL stage=builder

WORKDIR /app
COPY web/package.json web/package-lock.json ./
# 设置 npm 镜像源（优先使用官方源，若仍慢可换为国内源）
# 这里采用环境变量方式，方便通过 build-arg 覆盖
ARG NPM_REGISTRY=https://registry.npmjs.org/
RUN npm config set registry ${NPM_REGISTRY} && \
    npm install

COPY web .
RUN npm run build

# =====================

FROM python:3.13-alpine

ENV TZ Asia/Shanghai

WORKDIR /app

# 先执行依赖安装操作，后续如果依赖不变可以复用这一层
COPY backend/requirements.txt /app/requirements.txt

# 安装系统依赖和 Python 包，并清理缓存以减少镜像体积
RUN apk add --no-cache --virtual .build-deps build-base && \
    pip3 install --no-cache-dir -r requirements.txt && \
    apk add --no-cache tzdata && \
    apk add --no-cache nginx && \
    apk del .build-deps

# 复制前端编译文件到nginx默认路径
COPY --from=build-stage /app/dist /web
COPY docker/nginx.conf /etc/nginx/

# 复制项目代码到容器的app目录
COPY backend .

VOLUME [ "/app/config", "/app/data"]

EXPOSE 80

CMD [ "sh", "-c", "nginx && python3 run.py" ]




