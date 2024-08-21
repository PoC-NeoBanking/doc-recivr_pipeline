# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container at /usr/src/app
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port that will be set by the environment variable
# Use a default value in case the environment variable is not set
ENV PORT=3000
EXPOSE ${PORT}

# Run the application
CMD ["python", "run.py"]
