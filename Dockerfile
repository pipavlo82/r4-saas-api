FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app /app/app
ENV PORT=8082
# Читаємо порт з ENV (за замовчуванням 8082)
CMD ["sh","-lc","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8082}"]
