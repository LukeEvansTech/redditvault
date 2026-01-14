FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY webapp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application as a package
COPY webapp/ webapp/

# Environment variables (override in k8s/compose)
ENV DATABASE_URL=sqlite:////data/reddit_saved.db
ENV SECRET_KEY=change-me-in-production
ENV PYTHONPATH=/app

EXPOSE 5000

# Use gunicorn with preload to handle DB initialization before workers fork
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "--preload", "webapp.app:app"]
