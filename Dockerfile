FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY fixtures ./fixtures
RUN pip install --no-cache-dir .
ENV CLINIC_DB_PATH=/app/data/clinic.db
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["uvicorn", "clinic_agent_lab.api:app", "--host", "0.0.0.0", "--port", "8000"]
