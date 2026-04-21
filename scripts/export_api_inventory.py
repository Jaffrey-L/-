#!/usr/bin/env python3
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_FILE = ROOT / "app" / "main.py"
OUTPUT_FILE = ROOT / "docs" / "project" / "API兼容性盘点.md"


def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def extract_routes(source: str):
    tree = ast.parse(source)
    routes = []

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            if not isinstance(deco.func, ast.Attribute):
                continue
            if not isinstance(deco.func.value, ast.Name) or deco.func.value.id != "app":
                continue
            if deco.func.attr not in {"get", "post", "put", "delete", "patch", "api_route"}:
                continue

            path = _const_str(deco.args[0]) if deco.args else ""
            methods = []
            if deco.func.attr == "api_route":
                for kw in deco.keywords:
                    if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                        for e in kw.value.elts:
                            value = _const_str(e)
                            if value:
                                methods.append(value)
            else:
                methods = [deco.func.attr.upper()]

            routes.append(
                {
                    "path": path or "",
                    "methods": ",".join(methods) if methods else "UNKNOWN",
                    "handler": node.name,
                }
            )
    return routes


def classify(path: str):
    if path.startswith("/lx_openapi"):
        return "Lingxing OpenAPI"
    if path.startswith("/lx_web"):
        return "Lingxing WebAPI"
    if path.startswith("/ihr"):
        return "IHR360"
    if path.startswith("/k3"):
        return "Kingdee K3"
    if path.startswith("/mongodb"):
        return "Mongo View"
    if path.startswith("/meta"):
        return "Compatibility Meta"
    return "Internal/Utility"


def risk(path: str):
    if "{full_path:path}" in path:
        return "高（动态转发，边界广）"
    if path.startswith("/lx_openapi") or path.startswith("/lx_web"):
        return "中（外部依赖、限频影响）"
    if path.startswith("/ihr") or path.startswith("/k3"):
        return "中（外部系统依赖）"
    return "低"


def main():
    source = MAIN_FILE.read_text(encoding="utf-8")
    routes = extract_routes(source)
    routes = sorted(routes, key=lambda x: x["path"])

    lines = []
    lines.append("# API兼容性盘点")
    lines.append("")
    lines.append(f"- 生成来源：`{MAIN_FILE}`")
    lines.append(f"- 路由总数：`{len(routes)}`")
    lines.append("")
    lines.append("| 分组 | 路径 | 方法 | 处理函数 | 兼容风险 |")
    lines.append("|---|---|---|---|---|")
    for r in routes:
        lines.append(
            f"| {classify(r['path'])} | `{r['path']}` | `{r['methods']}` | `{r['handler']}` | {risk(r['path'])} |"
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

