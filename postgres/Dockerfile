FROM postgres:15.2-alpine

# Copy the SQL file into the container
COPY seraphim.sql /docker-entrypoint-initdb.d/

# Start the PostgreSQL server
CMD ["postgres"]