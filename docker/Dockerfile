FROM node:14.17-alpine as build-stage
LABEL stage=builder

WORKDIR /app
COPY web/package.json web/package-lock.json ./
RUN npm install

COPY web .
RUN npm run build

# =====================

FROM python:3.8-alpine

ENV TZ Asia/Shanghai

WORKDIR /app

# 必须安装了这个软件配置才会生效
RUN apk update && \
    apk add --no-cache tzdata && \
    apk add --no-cache nginx

# 先执行依赖安装操作，后续如果依赖不变可以复用这一层
COPY app/requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt

# 复制前端编译文件到nginx默认路径
COPY --from=build-stage /app/dist /web
COPY docker/nginx.conf /etc/nginx/

# 复制项目代码到容器的app目录
RUN mkdir -p /app/data/database /app/data/log /app/data/notebase
COPY app .

VOLUME [ "/app/config", "/app/data"]

EXPOSE 80

CMD [ "sh", "-c", "nginx && python3 app.py" ]




