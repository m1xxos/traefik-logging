FROM python:3.13-slim

ARG VEGETA_VERSION=12.13.0
ADD https://github.com/tsenart/vegeta/releases/download/v${VEGETA_VERSION}/vegeta_${VEGETA_VERSION}_linux_amd64.tar.gz /tmp/vegeta.tar.gz
RUN tar -xzf /tmp/vegeta.tar.gz -C /usr/local/bin vegeta && rm /tmp/vegeta.tar.gz

COPY app.py /app.py

EXPOSE 8000
CMD ["python3", "-u", "/app.py"]
