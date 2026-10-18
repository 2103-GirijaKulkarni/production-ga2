import logging
import time
import uuid
from collections import deque

from fastapi import FastAPI, Query, Request, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

EMAIL = "23f3000791@ds.study.iitm.ac.in"

app = FastAPI()

START_TIME = time.time()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"]
)

LOGS = deque(maxlen=1000)

logger = logging.getLogger("assignment")
logging.basicConfig(level=logging.INFO)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id

    started = time.perf_counter()
    response = await call_next(request)
    duration_s = time.perf_counter() - started

    path = request.url.path

    REQUEST_COUNT.labels(
        method=request.method,
        path=path,
        status=str(response.status_code)
    ).inc()

    log_entry = {
        "level": "INFO",
        "ts": time.time(),
        "path": path,
        "request_id": request_id,
        "method": request.method,
        "status": response.status_code,
        "duration_s": round(duration_s, 6)
    }

    LOGS.append(log_entry)
    logger.info("request completed", extra=log_entry)

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/work")
async def work(n: int = Query(default=1, ge=1, le=1_000_000)):
    total = 0
    for i in range(n):
        total += i

    return {
        "email": EMAIL,
        "done": n
    }


@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/healthz")
async def healthz():
    uptime_s = time.time() - START_TIME

    return {
        "status": "ok",
        "uptime_s": uptime_s
    }


@app.get("/logs/tail")
async def logs_tail(limit: int = Query(default=50, ge=1, le=1000)):
    return list(LOGS)[-limit:]
