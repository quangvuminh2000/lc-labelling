# Use an official Python runtime as a parent image
FROM python:3.8-slim
# Make port 8501 available to the world outside this container
EXPOSE 8501

# Install any needed packages specified in requirements.txt
RUN apt-get update && apt-get install -y \
    build-essential \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app



RUN pip3 install -r requirements.txt
# Define environment variable
#ENV NAME World

# Run app.py when the container launches
CMD ["streamlit","run", "main_page.py", "--server.port=8501", "--server.address=0.0.0.0"]
