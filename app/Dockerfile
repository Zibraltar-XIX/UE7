FROM python:3.14-slim

WORKDIR /app

COPY ./python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 5000

RUN useradd app
USER app

CMD ["python", "./python/app.py", "--host", "0.0.0.0", "--port", "5000"]