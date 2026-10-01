# payment-service

Independent **payment microservice** — Python / Flask — backed by its own
dedicated **PostgreSQL** database. A deliberately different stack from
`auth-service` to demonstrate that each microservice is built and deployed
independently. Standalone repository; only shares a Docker network.

## Endpoints

| Method | Path      | Description                                   |
| ------ | --------- | --------------------------------------------- |
| GET    | `/`       | Queries the DB and returns a success payload  |
| GET    | `/health` | Liveness check (no DB dependency)             |

Example success response:

```json
{ "service": "payment", "status": "success", "message": "Payment API is Live", "db": "connected", "transactions": 3 }
```

## Run locally

```bash
# once, if it doesn't already exist:
docker network create microservices-net

docker-compose up -d --build
curl http://localhost:5000/        # direct test
```

The frontend reaches it at `http://payment-service:5000` over `microservices-net`.

## Configuration (env vars)

| Variable      | Default       |
| ------------- | ------------- |
| `PORT`        | `5000`        |
| `DB_HOST`     | `payment-db`  |
| `DB_PORT`     | `5432`        |
| `DB_USER`     | `payment`     |
| `DB_PASSWORD` | `paymentpass` |
| `DB_NAME`     | `paymentdb`   |
