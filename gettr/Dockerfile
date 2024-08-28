# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container at /usr/src/app
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN apt-get update && apt-get install -y gcc
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port that will be set by the environment variable
# Use a default value in case the environment variable is not set
ENV PORT=2000
EXPOSE ${PORT}

# Set environment variables for Ollama connection and other constants
ENV PROMPT_TEMPLATE_PATH=./app/prompt.txt
ENV SERVER_URL=http://localhost:1000
ENV RECEIVER_URL=http://localhost:3000

# Run the application
CMD ["python", "run.py"]
