#
FROM python:3.11.8

#
WORKDIR /code

#
COPY requirements.txt /code/requirements.txt

#
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

#
COPY ./app /code/app
COPY ./lingxingopenapi /code/lingxingopenapi
#
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]