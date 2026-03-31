FROM python:3.11-slim

WORKDIR /app

COPY api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY packages/newgeo_core /app/packages/newgeo_core
RUN pip install --no-cache-dir -e /app/packages/newgeo_core

COPY api /app/api

CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

