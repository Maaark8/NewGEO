FROM python:3.11-slim

WORKDIR /app

COPY workers/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY packages/newgeo_core /app/packages/newgeo_core
RUN pip install --no-cache-dir -e /app/packages/newgeo_core

COPY workers /app/workers

CMD ["python3", "-m", "workers.app.worker"]

