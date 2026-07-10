FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

EXPOSE 8080

# RUN=poll (default) runs the polling bot — no public URL/webhook needed.
# RUN=webhook runs the FastAPI webhook adapter (APP_MODULE: twilio_bot / wa_bot).
ENV RUN=poll
ENV APP_MODULE=twilio_bot:app
CMD ["sh", "-c", "if [ \"$RUN\" = webhook ]; then uvicorn ${APP_MODULE} --host 0.0.0.0 --port ${PORT:-8080}; else python twilio_poll.py; fi"]
