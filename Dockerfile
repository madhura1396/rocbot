# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variables (optional, but good for defaults)
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV OLLAMA_HOST=http://localhost:11434 # Ollama usually runs on host, not in container
ENV OLLAMA_MODEL=llama3.2:latest

# Run app.py when the container launches
# CMD ["python", "backend/api/main.py"] 

# Use uvicorn directly to run the FastAPI app
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]