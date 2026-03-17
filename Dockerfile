FROM python:3.14-slim

WORKDIR /app

COPY ./site ./site
COPY ./python ./python

RUN pip install --no-cache-dir -r ./python/requirements.txt

EXPOSE 5000

CMD ["python", "./python/app.py"]