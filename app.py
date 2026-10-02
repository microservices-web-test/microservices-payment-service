# Payment microservice.
# A deliberately different stack from auth-service (Python/Flask instead of
# Node) to show that microservices are independently built and deployed. It
# talks to its OWN dedicated PostgreSQL database (payment-db).

import os

import psycopg2
from flask import Flask, jsonify

app = Flask(__name__)


def get_conn():
    # Connection details from environment variables (12-factor config).
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "payment-db"),
        port=os.environ.get("DB_PORT", "5432"),
        user=os.environ.get("DB_USER", "payment"),
        password=os.environ.get("DB_PASSWORD", "paymentpass"),
        dbname=os.environ.get("DB_NAME", "paymentdb"),
    )


@app.get("/")
def root():
    # Prove end-to-end connectivity by querying the database, then return success.
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM transactions")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return jsonify(
            service="payment",
            status="success",
            message="Payment API is Live",
            db="connected",
            transactions=count,
        )
    except Exception as exc:  # noqa: BLE001 - surface any DB error to the caller
        return (
            jsonify(service="payment", status="error", db="unreachable", error=str(exc)),
            500,
        )


@app.get("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
