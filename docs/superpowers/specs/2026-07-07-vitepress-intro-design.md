# VitePress 介绍站 — 设计文档

日期:2026-07-07

## 目标

用 VitePress 为 paste 仓库搭一个中文介绍站:一个 home 布局落地页 + 几页文档,讲清项目「是什么 / 怎么用 / 原理 / 怎么部署」。站点放在仓库 `docs/` 目录,与现有 Python 应用并存、互不干扰。

## 目录结构

全部新增在 `docs/` 下,不改动现有 `app.py` 和 `deploy/`:

```
docs/
├── package.json              # vitepress 依赖 + dev/build/preview 脚本
├── .vitepress/
│   └── config.mts            # 站点配置:中文、导航栏、侧边栏
├── index.md                  # 首页:home 布局(hero + features)
├── guide/
│   ├── getting-started.md    # 快速开始:运行、环境变量表
│   └── how-it-works.md       # 工作原理:路径映射、自动保存、安全设计
└── deploy.md                 # 部署:systemd + Caddy
```

## 各页内容

- **首页 `index.md`** — VitePress `layout: home`。hero 区:标题「paste」、tagline「极简文本中转站」、一段 text 描述、CTA 按钮(「快速开始」跳 `/guide/getting-started`、「GitHub」跳仓库)。features 区 4 个卡片:零依赖(只用 Python 标准库)、路径动态映射(`/note ⟷ notes/note.txt`)、静默自动保存(输入停顿后自动写盘)、极简无按钮(全靠 URL 控制)。
- **快速开始 `guide/getting-started.md`** — `python3 app.py` 运行方式,`HOST` / `PORT` / `NOTES_DIR` 环境变量表(沿用 README),根路径 `/` 重定向到 `/note` 的说明。
- **工作原理 `guide/how-it-works.md`** — 相比 README 的增量价值。讲清三点:①路径映射(`safe_path` 把 `/name` 映射到 `notes/name.txt`,不存在则首次保存时创建);②静默自动保存(input debounce 600ms、blur/visibilitychange/beforeunload 兜底、`sendBeacon` 离开页面保存、请求串行化避免并发覆盖);③安全设计(`NAME_RE` 校验名字、拒绝 `..`、`commonpath` 双保险防路径穿越、临时文件 + `os.replace` 原子写)。
- **部署 `deploy.md`** — systemd 单元(`deploy/paste.service`,监听 `127.0.0.1:8088`、开机自启、崩溃重启、基础加固)+ Caddy 反代(`deploy/paste.qixin.ch.conf`,自动 HTTPS、`max_size 50MB`)两段配置,附上 README 里 `admin off` 时要 `restart` 而非 `reload` 的注意事项。

## 配置要点

- `.vitepress/config.mts`:`lang: 'zh-CN'`、`title: 'paste'`、`description` 一句话定位;导航栏(指南 / 部署 / GitHub 链接);侧边栏 `/guide/` 分组(快速开始、工作原理)。
- `package.json`:`devDependencies` 加 `vitepress`(最新稳定版),scripts:`docs:dev` / `docs:build` / `docs:preview`。
- 根 `.gitignore` 追加:`docs/node_modules/`、`docs/.vitepress/cache/`、`docs/.vitepress/dist/`。
- 使用 VitePress 默认主题,不加自定义 CSS —— 契合「极简」调性,也最省维护。

## 不做(YAGNI)

i18n 双语、自定义 Vue 组件、内嵌 live demo、CI/部署工作流。除非后续明确需要。

## 验收

- `cd docs && npm install && npm run docs:build` 构建成功、无报错。
- `npm run docs:dev` 起本地服务,首页 hero/features 正常、四页导航互通、内容与 README/代码一致。
