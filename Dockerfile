FROM python:3.8-slim

WORKDIR /app

COPY server.py ./

EXPOSE 8000

CMD ["python", "server.py"]
