# Python image to use.
FROM python:3.9

# Set the working directory to /app
WORKDIR /app

# copy the requirements file used for dependencies
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Copy the rest of the working directory contents into the container at /app
COPY . .

# Expose the port on which the application will run
EXPOSE 8082

RUN apt-get update && apt-get install -y cron

# Run the application
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8082", "--noreload"]
