from typing import Any, Dict, List

from fastapi import Request


def is_compat_envelope_enabled(request: Request) -> bool:
    qp = request.query_params.get("_compat_envelope")
    header = request.headers.get("X-Compat-Envelope")
    return qp == "1" or header == "1"


def envelope(payload: Any, request_id: str, source: str, message: str = "success", code: int = 0) -> Dict[str, Any]:
    if isinstance(payload, dict) and {"code", "message", "data"}.issubset(payload.keys()):
        normalized = dict(payload)
        normalized.setdefault("request_id", request_id)
        normalized.setdefault("source", source)
        return normalized
    return {
        "code": code,
        "message": message,
        "data": payload,
        "request_id": request_id,
        "source": source,
    }


def maybe_envelope(request: Request, payload: Any, source: str, message: str = "success", code: int = 0) -> Any:
    if not is_compat_envelope_enabled(request):
        return payload
    request_id = getattr(request.state, "request_id", "")
    return envelope(payload=payload, request_id=request_id, source=source, message=message, code=code)


def compatibility_routes() -> List[Dict[str, str]]:
    return [
        {"group": "Lingxing OpenAPI", "path": "/lx_openapi/{full_path:path}", "status": "running"},
        {"group": "Lingxing WebAPI", "path": "/lx_web/{full_path:path}", "status": "running"},
        {"group": "IHR360", "path": "/ihr/{full_path:path}", "status": "running"},
        {"group": "Kingdee K3", "path": "/k3/*", "status": "running"},
        {"group": "Mongo View", "path": "/mongodb/view/", "status": "legacy"},
        {"group": "Utility", "path": "/healthz,/generate_dates/,/clear_table", "status": "running"},
    ]

