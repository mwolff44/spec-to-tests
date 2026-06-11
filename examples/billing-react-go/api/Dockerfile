FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod go.sum* ./
RUN go mod download || true
COPY . .
RUN CGO_ENABLED=0 go build -o /out/billing .

FROM alpine:3.20
RUN apk add --no-cache wget
COPY --from=build /out/billing /usr/local/bin/billing
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/billing"]
