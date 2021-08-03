FROM python:3.8-alpine

# 先执行依赖安装操作，后续如果依赖不变可以复用这一层
COPY app/requirements.txt /requirements.txt

WORKDIR /

RUN pip3 install -r requirements.txt

# 复制项目代码到容器的app目录
COPY app /app

VOLUME [ "/app/config", "/app/log", "/app/filebase", "/app/notebase"]

EXPOSE 4231

# 使用ENTRYPOINT限制容器只能执行下面的指令
ENTRYPOINT [ "python3", "/app/app.py"]