"""FastAPI application: ``uvicorn amcrax.api.main:app --port 8000``."""
from __future__ import annotations

import json
import logging
import logging.config
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from amcrax import paths

from .errors import install_handlers
from .routers import core, data, domain, reports, simulation


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        d = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"), "level": record.levelname,
             "logger": record.name, "msg": record.getMessage()}
        for k in ("method", "path", "status", "ms"):
            if hasattr(record, k):
                d[k] = getattr(record, k)
        if record.exc_info:
            d["exc"] = self.formatException(record.exc_info)
        return json.dumps(d)


def setup_logging() -> None:
    handlers = {"console": {"class": "logging.StreamHandler", "formatter": "json"}}
    try:
        log_dir = paths.ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        handlers["file"] = {"class": "logging.FileHandler", "filename": str(log_dir / "api.log"),
                            "formatter": "json", "encoding": "utf-8"}
    except OSError:
        pass
    logging.config.dictConfig({
        "version": 1, "disable_existing_loggers": False,
        "formatters": {"json": {"()": JsonFormatter}},
        "handlers": handlers,
        "loggers": {"amcrax": {"handlers": list(handlers), "level": "INFO", "propagate": False}},
    })


setup_logging()
log = logging.getLogger("amcrax.api")

app = FastAPI(title="AmCraX API", version="1.0.0",
              description="Ammonia cracking simulation and optimisation platform backend")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["Content-Disposition", "Location"])
install_handlers(app)


@app.middleware("http")
async def access_log(request: Request, call_next):
    t = time.perf_counter()
    response = await call_next(request)
    log.info("request", extra={"method": request.method, "path": request.url.path,
                               "status": response.status_code, "ms": round((time.perf_counter() - t) * 1000, 1)})
    return response


app.include_router(core.router)
app.include_router(simulation.router)
app.include_router(domain.router)
app.include_router(data.router)
app.include_router(reports.router)

for _mount, _dir in (("/aspen-screenshots", paths.ASPEN_SCREENSHOTS), ("/dashboard-screenshots", paths.DOCS_DIR / "screenshots")):
    if _dir.exists():
        app.mount(_mount, StaticFiles(directory=str(_dir)), name=_mount.strip("/"))

paths.RESULTS_FIGURES.mkdir(parents=True, exist_ok=True)
app.mount("/figures", StaticFiles(directory=str(paths.RESULTS_FIGURES)), name="figures")
