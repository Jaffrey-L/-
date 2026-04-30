# 镜像构建
```shell
docker build -t swr.cn-south-1.myhuaweicloud.com/jetems/syncapp:0.2 .
```

# 镜像压缩
```shell
sudo docker-slim build --include-shell swr.cn-south-1.myhuaweicloud.com/jetems/syncapp:0.2
```

# 镜像推送
```shell
docker push swr.cn-south-1.myhuaweicloud.com/jetems/syncapp.slim:latest
```

# 本地联调（阶段1）

## 1) 配置环境变量

复制 `.env.example` 为 `.env`，至少填好以下项：

- `LINGXING_APP_ID`
- `LINGXING_APP_SECRET`
- `LINGXING_WEB_ACCOUNT`
- `LINGXING_WEB_PASSWORD`
- `MYSQL_*`（若仍从 MySQL 取 token）

## 2) 启动中间件

```shell
python -m app.main
```

默认端口：`8088`

## 3) 快速自检

PowerShell 执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1
```

## 4) ETL 配置原则

- ETL 只传业务参数（日期、offset、length 等）
- ETL 不传 `token/sign`
- 由中间件统一处理鉴权、签名和重试

## 5) 阶段1通过标准

- `/healthz` 返回 `{"status":"ok"}`
- ETL 调用 `lx_openapi` 接口返回业务成功
- 分页任务能正确停止，不重复拉取

## 6) 生产稳定性建议（systemd）

推荐改为 `systemd` 托管，避免手工 `nohup` 带来的进程丢失和端口占用问题。

```bash
cd /opt/lingxing-middleware/app
git pull myrepo main
chmod +x deploy/systemd/install_systemd_service.sh
sudo bash deploy/systemd/install_systemd_service.sh
```
