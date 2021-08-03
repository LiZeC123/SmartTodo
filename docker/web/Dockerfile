FROM node:14.17-alpine as build-stage
LABEL stage=builder

WORKDIR /app
COPY web/package.json web/package-lock.json ./
RUN npm install

COPY web .
RUN npm run build

# =====================

FROM nginx:1.21.1-alpine as production-stage
COPY ./docker/web/nginx.conf /etc/nginx/
COPY --from=build-stage /app/dist /app

VOLUME [ "/app/filebase" ]

EXPOSE 80

# 使用daemon off的方式将nginx运行在前台保证镜像不至于退出
CMD ["nginx", "-g", "daemon off;"]
