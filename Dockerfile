# ==============================================================================
# Dockerfile for Building Analytics Frontend (Chainlit Web Application)
# ==============================================================================

# 1. Base Image: Lightweight Python 3.11 Linux container
FROM python:3.11-slim

# Prevent Python from writing .pyc files to disk and enable instant unbuffered stdout/stderr logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Cloud Run injects $PORT (defaults to 8080)
ENV PORT=8080

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Install dependencies first (leverages Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 4. Copy the frontend application code
COPY . /app/front

# 5. Tell Python that /app is in the Python module search path
ENV PYTHONPATH=/app

# 6. Expose the port (informative documentation for container runners)
EXPOSE 8080

# 7. Start Chainlit listening on 0.0.0.0 and port 8080 (Cloud Run requirement)
CMD ["sh", "-c", "chainlit run front/app.py --host 0.0.0.0 --port ${PORT} --headless"]
