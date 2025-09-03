# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv for faster dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src ./src

# Install dependencies using uv
RUN uv sync --frozen

# Copy source code
COPY src/ ./src/

# Set the working directory to src for the application
WORKDIR /app/src

# Expose port 8000
EXPOSE 8000

# Set up healthcheck to ensure the application is running
RUN apt-get update && apt-get install -y curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
  CMD curl -f http://localhost:8000/favicon || exit 1

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
