FROM python:3.14-slim

WORKDIR /app

COPY ./python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --shell /bin/bash app

COPY --chown=app:app . .

EXPOSE 5000

USER app

CMD ["python", "./python/app.py"]