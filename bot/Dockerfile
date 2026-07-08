FROM python:3.11-slim
WORKDIR /app/backend

# Ставим зависимости бэкенда, т.к. бот переиспользует его модели (app.models, app.db, app.config)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app

WORKDIR /app/bot
COPY bot/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY bot/bot.py ./bot.py

ENV PYTHONPATH=/app/backend

CMD ["python", "bot.py"]
