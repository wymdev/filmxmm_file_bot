FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && addgroup --system bot \
    && adduser --system --ingroup bot bot \
    && chown bot:bot /app

COPY --chown=bot:bot . .

USER bot

CMD ["python3", "bot.py"]
