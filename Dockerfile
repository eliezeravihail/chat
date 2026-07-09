FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core.py wa_bot.py twilio_bot.py .

EXPOSE 8080

# APP_MODULE selects the adapter: twilio_bot:app (default) or wa_bot:app (Meta).
ENV APP_MODULE=twilio_bot:app
CMD ["sh", "-c", "uvicorn ${APP_MODULE} --host 0.0.0.0 --port ${PORT:-8080}"]
