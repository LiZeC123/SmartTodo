FROM python:3.8-alpine

COPY ../app/requirements.txt /requirements.txt

WORKDIR /

RUN pip3 install -r requirements.txt

COPY ../app /

ENTRYPOINT [ "python3" ]

CMD [ "app/app.py" ] 