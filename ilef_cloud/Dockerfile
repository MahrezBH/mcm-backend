# Use the official Python image from the Docker Hub
FROM python:3.8-slim-buster

# Set environment variables to ensure that Python outputs everything to the terminal without buffering it.
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY ilef_cloud/requirements.txt /app/

# Install the required packages
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the entire backend project to the working directory
COPY ilef_cloud /app/

# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]