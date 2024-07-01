# 制作 image
```shell
docker build -t swr.cn-south-1.myhuaweicloud.com/jetems/syncapp:0.2 .
```

# 压缩 image
```shell
sudo docker-slim build --include-shell swr.cn-south-1.myhuaweicloud.com/jetems/syncapp:0.2
```

# 推送 image
```shell
docker push swr.cn-south-1.myhuaweicloud.com/jetems/syncapp.slim:latest
```
