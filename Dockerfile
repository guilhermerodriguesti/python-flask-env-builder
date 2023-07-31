# Use the official Python image as the base image
FROM python:3.8-alpine

ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files into the container
COPY . .

# Expose the port that Flask will be running on
EXPOSE 8000

# Define the command to run the Flask application
CMD ["python", "app.py"]
