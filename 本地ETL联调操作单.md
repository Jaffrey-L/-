# 本地 ETL 联调操作单（阶段1）

## 目标
验证本地 ETL 可以通过中间件正常访问领星 API，并由中间件托管鉴权和签名。

## 前置条件
1. 中间件代码已更新到最新。
2. `.env` 已配置敏感参数。
3. 本机可访问领星 API。

## 步骤A：启动中间件
```bash
python -m app.main
```

## 步骤B：基础健康检查
```powershell
Invoke-RestMethod http://127.0.0.1:8088/healthz
```
预期：返回 `status=ok`

## 步骤C：样例接口验证（OrderProfit）
ETL 中 API 节点配置：
- Method: `POST`
- URL: `http://127.0.0.1:8088/lx_openapi/basicOpen/finance/mreport/OrderProfit`
- Body(JSON):
```json
{
  "offset": 0,
  "length": 1000,
  "startDate": "${report_date}",
  "endDate": "${report_date}",
  "currencyCode": "CNY"
}
```

## 步骤D：分页验证
1. offset 从 0 开始。
2. 每次 +length。
3. 当返回条数 `< length` 时停止。

## 通过标准
1. ETL 可稳定拿到数据。
2. ETL 未配置 token/sign。
3. 中间件日志可见请求和错误信息。
4. 异常请求可重试成功。

## 常见问题
1. 401/签名错误：检查 `.env` 中 `LINGXING_APP_ID`、`LINGXING_APP_SECRET`。
2. 连接失败：确认 ETL 访问的是中间件地址，不是领星直连地址。
3. 空数据：先固定单日时间范围验证，再放大时间窗口。
