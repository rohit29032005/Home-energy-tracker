FROM python:3.13-slim

WORKDIR /app
COPY ml-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ml-service/app /app/ml-service/app
COPY ml-service/models /app/ml-service/models
WORKDIR /app/ml-service

# The artefact is generated reproducibly by training/train.py from the root CSV
# and evaluated before packaging. Serving must not retrain on container startup.
RUN python -c "from app.main import MODEL_PATH, METADATA_PATH; assert MODEL_PATH.exists() and METADATA_PATH.exists()"

EXPOSE 8090
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
