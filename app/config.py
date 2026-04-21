import os
from typing import List
from pathlib import Path


def _load_local_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_local_env_file()


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_list(value: str, default: List[str]) -> List[str]:
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


class Config:
    OPENAPI_HOST = os.getenv("LINGXING_OPENAPI_HOST", "https://openapi.lingxing.com")
    WEB_HOST = os.getenv("LINGXING_WEB_HOST", "https://gw.lingxingerp.com")
    FRONTEND_HOST = os.getenv("LINGXING_FRONTEND_HOST", "https://vayi.lingxing.com")

    APP_ID = os.getenv("LINGXING_APP_ID", "ak_dLMBP259Pb5wH")
    APP_SECRET = os.getenv("LINGXING_APP_SECRET", "BYKn4e/XVg+shbQPVbMjiQ==")

    WEB_ACCOUNT = os.getenv("LINGXING_WEB_ACCOUNT", "vayiapi")
    WEB_PASSWORD = os.getenv("LINGXING_WEB_PASSWORD", "7KYx#ChlWu8d6]}T")
    AUTH_CACHE_FILE = os.getenv("LINGXING_AUTH_CACHE_FILE", "auth.json")
    AUTH_CACHE_TTL_SECONDS = int(os.getenv("LINGXING_AUTH_CACHE_TTL_SECONDS", "430000"))

    MYSQL_HOST = os.getenv("MYSQL_HOST", "192.168.1.191")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Dk03Bt3409abc")
    MYSQL_DB = os.getenv("MYSQL_DB", "api_access_token")

    PG_HOST = os.getenv("PG_HOST", "192.168.1.227")
    PG_PORT = int(os.getenv("PG_PORT", "5432"))
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PASSWORD = os.getenv("PG_PASSWORD", "vayiERty123")
    PG_DATABASE = os.getenv("PG_DATABASE", "postgres")
    PG_SCHEMA = os.getenv("PG_SCHEMA", "vayidw")

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://vayi:vayi12aBde@192.168.1.223:27017/")
    MONGO_DB = os.getenv("MONGO_DB", "lingxing")
    MONGO_VIEW_URI = os.getenv("MONGO_VIEW_URI", "mongodb://192.168.1.181:27017/")
    MONGO_VIEW_DB = os.getenv("MONGO_VIEW_DB", "my_database")

    K3_APP_ID = os.getenv("K3_APP_ID", "66ec14697e30c9")
    K3_ACCOUNT = os.getenv("K3_ACCOUNT", "kd")
    K3_APP_SECRET = os.getenv("K3_APP_SECRET", "290636_XefN38hGVkAewXWPQ40O6YSNQI0VSAqG")
    K3_SERVICE_SECRET = os.getenv("K3_SERVICE_SECRET", "e8a38bef8a174933853cddb4728e7f56")
    K3_BASE_URL = os.getenv("K3_BASE_URL", "http://erp.vayi.cn:8090/k3cloud")

    ALLOWED_TABLES = _as_list(
        os.getenv("ALLOWED_TRUNCATE_TABLES", "lx_web_fba_inventory,lx_inventory_by_wyt,kd_v_just_inventory_eng"),
        ["lx_web_fba_inventory", "lx_inventory_by_wyt", "kd_v_just_inventory_eng"],
    )
    OPENAPI_ALLOWED_PATHS = _as_list(
        os.getenv("OPENAPI_ALLOWED_PATHS", ""),
        [],
    )
    WEB_ALLOWED_HOSTS = _as_list(
        os.getenv("WEB_ALLOWED_HOSTS", "gw.lingxingerp.com,vayi.lingxing.com"),
        ["gw.lingxingerp.com", "vayi.lingxing.com"],
    )
    ENFORCE_OPENAPI_WHITELIST = _as_bool(os.getenv("ENFORCE_OPENAPI_WHITELIST"), default=False)
    ENFORCE_WEB_HOST_WHITELIST = _as_bool(os.getenv("ENFORCE_WEB_HOST_WHITELIST"), default=True)
