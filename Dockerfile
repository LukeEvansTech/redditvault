FROM python:3.14-slim

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
# Run as non-root (least-privilege).
RUN chown -R 1000:1000 /app
USER 1000:1000
# Health check via TCP socket on the listening port — no extra deps,
# works for any uvicorn/gunicorn/asgi listener.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import socket,sys;s=socket.socket();s.settimeout(2);s.connect(('127.0.0.1',5000));s.close()" || exit 1
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "--preload", "webapp.app:app"]
