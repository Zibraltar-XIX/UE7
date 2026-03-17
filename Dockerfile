FROM python:3.14-slim

WORKDIR /app

COPY site/css ./site/css
COPY site/html ./site/html
COPY site/src ./site/src
COPY ./python .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]