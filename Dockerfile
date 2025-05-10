# Use a Python base image (adjust the version as needed)
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the application code into the container
COPY app /app

# Copy the requirements file (if you have one)
COPY requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install pytest and requests-mock
RUN pip install --no-cache-dir pytest requests_mock

# Set the entrypoint to run tests.  Important.
ENTRYPOINT ["pytest", "tests"]