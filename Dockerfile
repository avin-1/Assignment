# --- Stage 1: Build the Vite frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Install dependencies first for better caching
COPY frontend/package*.json ./
RUN npm ci

# Copy the rest of the frontend source and build
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Build the Python backend ---
FROM python:3.13-slim

# Create a non-root user specifically for running the app on huggingface spaces
# See: https://huggingface.co/docs/spaces/docker#user
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy requirements and install
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files
COPY --chown=user . .

# Copy the built frontend static files from Stage 1
COPY --chown=user --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose the standard Hugging Face Spaces port
EXPOSE 7860

# Run the app
CMD ["python", "main.py"]
