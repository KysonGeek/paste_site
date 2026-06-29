# paste

极简的文本中转站:访问 `/任意名字` 打开一个全屏文本框,内容变动时自动保存到本地 txt 文件,方便在电脑和手机之间互相复制内容。

- 零依赖,只用 Python 标准库
- 路径动态映射:`/note` ⟷ `notes/note.txt`,不存在则首次保存时创建
- 页面极简,无任何按钮,全靠 URL 控制;输入停顿后静默自动保存
- 根路径 `/` 重定向到 `/note`

## 运行

```bash
python3 app.py
# 默认监听 0.0.0.0:8000,数据存到 ./notes/
```

环境变量:

| 变量 | 默认 | 说明 |
|------|------|------|
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `8000` | 监听端口 |
| `NOTES_DIR` | `./notes` | txt 文件存放目录 |

## 部署

`deploy/` 下提供参考配置:

- `paste.service` — systemd 服务单元(监听 `127.0.0.1:8088`,开机自启、崩溃重启)
- `paste.qixin.ch.conf` — Caddy 反代站点配置(自动 HTTPS)

> 注意:若 Caddy 全局配了 `admin off`,改完配置要用 `systemctl restart caddy`,`reload` 会失败。
