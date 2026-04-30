# Systemd 托管部署说明

## 目标
把 `uvicorn` 从手工 `nohup` 改为 `systemd` 托管，提升稳定性与可恢复能力。

## 文件
- `deploy/systemd/lingxing-middleware.service`
- `deploy/systemd/install_systemd_service.sh`

## 本地完成后，云端更新步骤
```bash
cd /opt/lingxing-middleware/app
git pull myrepo main
chmod +x deploy/systemd/install_systemd_service.sh
sudo bash deploy/systemd/install_systemd_service.sh
```

## 常用运维命令
```bash
sudo systemctl status lingxing-middleware.service
sudo systemctl restart lingxing-middleware.service
sudo systemctl stop lingxing-middleware.service
sudo journalctl -u lingxing-middleware.service -f
```

## 验证
```bash
curl -sS http://127.0.0.1:8088/healthz
curl -sS -m 90 http://127.0.0.1:8088/lx_openapi/basicOpen/finance/mreport/OrderProfit \
  -H 'Content-Type: application/json' \
  -d '{"offset":0,"length":200,"startDate":"2026-04-01","endDate":"2026-04-01","currencyCode":"CNY"}'
```
