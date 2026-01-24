FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy environment file
COPY environment.yml .
COPY requirements.txt .
COPY requirements-dev.txt .

# Create conda environment
RUN conda env create -f environment.yml

# Activate conda environment in the shell
SHELL ["conda", "run", "-n", "mannings-sla", "/bin/bash", "-c"]

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data logs outputs

# Expose port for Streamlit
EXPOSE 8501

# Command to run the application
CMD ["conda", "run", "-n", "mannings-sla", "streamlit", "run", "src/visualization/dashboard/app.py"]
