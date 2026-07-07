# 部署

生产环境推荐:用 systemd 把 `app.py` 跑成常驻服务,只监听本地端口;再用 Caddy 反向代理并自动签发 HTTPS。仓库 `deploy/` 目录下提供了可直接参考的配置。

下面以部署到 `/opt/app/paste_site`、域名 `paste.qixin.ch` 为例。

## systemd 服务

`deploy/paste.service` 让服务监听 `127.0.0.1:8088`、开机自启、崩溃自动重启,并做了基础加固:

```ini
[Unit]
Description=paste.qixin.ch - simple txt paste site
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/app/paste_site
Environment=HOST=127.0.0.1
Environment=PORT=8088
Environment=NOTES_DIR=/opt/app/paste_site/notes
ExecStart=/usr/bin/python3 /opt/app/paste_site/app.py
Restart=on-failure
RestartSec=2

# 基础加固
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/opt/app/paste_site/notes

[Install]
WantedBy=multi-user.target
```

启用:

```bash
sudo cp deploy/paste.service /etc/systemd/system/paste.service
sudo systemctl daemon-reload
sudo systemctl enable --now paste
sudo systemctl status paste
```

::: tip 加固说明
`ProtectSystem` / `ProtectHome` / `PrivateTmp` 会把大部分文件系统设为只读或隔离,所以必须用 `ReadWritePaths` 显式放开数据目录,否则服务无法写入 `notes/`。
:::

## Caddy 反向代理

`deploy/paste.qixin.ch.conf` 把域名反代到本地服务,Caddy 会自动申请并续期 HTTPS 证书:

```text
paste.qixin.ch {
	request_body {
		max_size 50MB
	}
	reverse_proxy 127.0.0.1:8088
}
```

`max_size 50MB` 放宽了请求体上限,方便贴较大的文本。把这段并入你的 Caddyfile(或作为独立站点文件被 import)后重载 Caddy 即可。

::: warning 注意
若 Caddy 全局配了 `admin off`,改完配置要用 `systemctl restart caddy` 生效,`reload` 会失败。
:::
