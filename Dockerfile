FROM python:3.14-slim

WORKDIR /app

COPY ./css ./site/css
COPY ./html ./site/html
COPY ./src ./site/src
COPY ./python .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]