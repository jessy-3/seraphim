FROM golang:latest

WORKDIR /app
COPY . .

RUN go mod download
RUN go build -o gobackend .

EXPOSE 8083
CMD [ "./gobackend" ]
