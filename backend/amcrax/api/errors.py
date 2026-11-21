"""Consistent error model ``{code, message, detail}`` and shared helpers."""
from __future__ import annotations

import dataclasses
import importlib
import inspect
import math
from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, detail: Any = None):
        super().__init__(message)
        self.status, self.code, self.message, self.detail = status, code, message, detail


def err_body(code: str, message: str, detail: Any = None) -> dict:
    return {"code": code, "message": message, "detail": detail}


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, e: ApiError):
        return JSONResponse(err_body(e.code, e.message, e.detail), status_code=e.status)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(e.status_code, "http_error")
        return JSONResponse(err_body(code, str(e.detail)), status_code=e.status_code)

    @app.exception_handler(RequestValidationError)
    async def _val(_: Request, e: RequestValidationError):
        return JSONResponse(
            err_body("validation_error", "Request validation failed", jsonable(e.errors())),
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def _any(request: Request, e: Exception):
        import logging

        logging.getLogger("amcrax.api").exception("unhandled error on %s", request.url.path)
        return JSONResponse(err_body("internal_error", f"{type(e).__name__}: {e}"), status_code=500)


def jsonable(obj: Any) -> Any:
    """Convert pydantic / dataclass / numpy / NaN structures into strict-JSON-safe values."""
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if hasattr(obj, "model_dump"):
        return jsonable(obj.model_dump(mode="json"))
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return jsonable(dataclasses.asdict(obj))
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(v) for v in obj]
    if hasattr(obj, "tolist"):  # numpy
        return jsonable(obj.tolist())
    if hasattr(obj, "item"):
        return jsonable(obj.item())
    if hasattr(obj, "__dict__"):
        return jsonable({k: v for k, v in vars(obj).items() if not k.startswith("_")})
    return str(obj)


def lazy_module(name: str):
    """Import ``amcrax.<name>`` or raise a 503 ``module_unavailable``."""
    full = f"amcrax.{name}"
    try:
        return importlib.import_module(full)
    except Exception as e:  # ImportError or a half-written module
        raise ApiError(503, "module_unavailable", f"Module {full} is not available yet",
                       {"module": full, "error": f"{type(e).__name__}: {e}"})


def lazy_attr(module: str, *names: str) -> Callable:
    """First existing attribute among ``names`` in ``amcrax.<module>`` else 503."""
    mod = lazy_module(module)
    for n in names:
        fn = getattr(mod, n, None)
        if fn is not None:
            return fn
    raise ApiError(503, "module_unavailable",
                   f"amcrax.{module} does not provide any of {list(names)} yet",
                   {"module": f"amcrax.{module}", "wanted": list(names)})


def call_flex(fn: Callable, *args, **kwargs):
    """Call ``fn`` passing only the keyword arguments its signature accepts; wrap failures as 500/422."""
    try:
        sig = inspect.signature(fn)
        if not any(p.kind is p.VAR_KEYWORD for p in sig.parameters.values()):
            kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
    except (TypeError, ValueError):
        pass
    try:
        return fn(*args, **kwargs)
    except ApiError:
        raise
    except (ValueError, KeyError) as e:
        raise ApiError(422, "calculation_error", f"{type(e).__name__}: {e}")
    except Exception as e:
        raise ApiError(500, "calculation_failed", f"{type(e).__name__}: {e}")
