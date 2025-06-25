# Use official Miniconda3 base image
FROM continuumio/miniconda3

# Set working directory
WORKDIR /app

# Copy environment.yml first
COPY environment.yml .

# Create the conda environment from environment.yml
RUN conda env create -f environment.yml

# Make RUN commands use the new environment:
SHELL ["conda", "run", "-n", "env", "/bin/bash", "-c"]

# Activate env in future commands
RUN echo "source activate env" >> ~/.bashrc
ENV PATH /opt/conda/envs/env/bin:$PATH
ENV PYTHONPATH=/app

# Copy your app code
COPY . .

# Expose the port (optional but good practice)
EXPOSE 8000

# Run FastAPI with Uvicorn in the conda environment
CMD ["uvicorn", "backend.assistant_app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]