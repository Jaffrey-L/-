# API兼容性盘点

- 生成来源：`D:\知识地图\领星API代码分析\lingxingsync\app\main.py`
- 路由总数：`16`

| 分组 | 路径 | 方法 | 处理函数 | 兼容风险 |
|---|---|---|---|---|
| Internal/Utility | `/clear_table` | `POST` | `clear_table` | 低 |
| Internal/Utility | `/generate_dates/` | `GET` | `generate_dates` | 低 |
| Internal/Utility | `/healthz` | `GET` | `healthz` | 低 |
| IHR360 | `/ihr/openapi/thirdparty/api/staff/v1/staffs` | `GET` | `ihr_staffs` | 中（外部系统依赖） |
| IHR360 | `/ihr/{full_path:path}` | `GET,POST,PUT,DELETE,OPTIONS,HEAD,PATCH,TRACE` | `ihr_proxy_request` | 高（动态转发，边界广） |
| Kingdee K3 | `/k3/bill_query` | `POST` | `k3_bill_query` | 中（外部系统依赖） |
| Kingdee K3 | `/k3/query_bussiness_info` | `POST` | `k3_query_bussiness_info` | 中（外部系统依赖） |
| Kingdee K3 | `/k3/stock_report` | `POST` | `k3_stock_report_query` | 中（外部系统依赖） |
| Kingdee K3 | `/k3/sys_report_query` | `POST` | `k3_sys_report_query` | 中（外部系统依赖） |
| Internal/Utility | `/log_response` | `POST` | `log_response` | 低 |
| Internal/Utility | `/lx_downfile` | `GET` | `lx_downfile` | 低 |
| Lingxing OpenAPI | `/lx_openapi/erp/sc/routing/data/local_inventory/batchGetProductInfo` | `POST` | `lx_batch_get_product_info` | 中（外部依赖、限频影响） |
| Lingxing OpenAPI | `/lx_openapi/{full_path:path}` | `GET,POST,PUT,DELETE,OPTIONS,HEAD,PATCH,TRACE` | `lx_api_proxy_request` | 高（动态转发，边界广） |
| Lingxing WebAPI | `/lx_web/{full_path:path}` | `GET,POST,PUT,DELETE,OPTIONS,HEAD,PATCH,TRACE` | `lx_web_proxy_request` | 高（动态转发，边界广） |
| Compatibility Meta | `/meta/compatibility/routes` | `GET` | `meta_compatibility_routes` | 低 |
| Mongo View | `/mongodb/view/` | `POST` | `get_items` | 低 |
