#
FROM python:3.11.8

#
WORKDIR /code

#
COPY requirements.txt /code/requirements.txt
COPY kingdee.cdp.webapi.sdk-8.0.4-py3-none-any.whl /code/kingdee.cdp.webapi.sdk-8.0.4-py3-none-any.whl
#
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
RUN pip install --no-cache-dir /code/kingdee.cdp.webapi.sdk-8.0.4-py3-none-any.whl

#
COPY ./app /code/app
COPY ./lingxingopenapi /code/lingxingopenapi
#
EXPOSE 80
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]