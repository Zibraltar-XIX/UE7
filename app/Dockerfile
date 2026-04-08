FROM python:3.14-slim

RUN apk update && apk upgrade --no-cache

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd app
USER app

CMD ["python", "./python/app.py", "--host", "0.0.0.0", "--port", "5000"]