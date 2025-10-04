# Use the official Redis image as the parent image
FROM redis

# Set the working directory to /app
WORKDIR /app

# Copy the redis configuration file to the container
COPY redis.conf /usr/local/etc/redis/redis.conf

# Expose the Redis port
EXPOSE 6379

# Start the Redis server using the configuration file
CMD [ "redis-server", "/usr/local/etc/redis/redis.conf" ]
