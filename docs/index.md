---
layout: home

hero:
  name: paste
  text: 极简文本中转站
  tagline: 访问 /任意名字 打开一个全屏文本框,内容变动时自动保存到本地 txt。方便在电脑和手机之间互相复制内容。
  actions:
    - theme: brand
      text: 快速开始
      link: /guide/getting-started
    - theme: alt
      text: 工作原理
      link: /guide/how-it-works
    - theme: alt
      text: GitHub
      link: https://github.com/KysonGeek/paste_site

features:
  - icon: 🪶
    title: 零依赖
    details: 只用 Python 标准库,单文件 app.py。一条 python3 app.py 就能跑,不装任何包。
  - icon: 🔗
    title: 路径动态映射
    details: /note ⟷ notes/note.txt。URL 里换个名字就是另一份 paste,文件不存在则首次保存时自动创建。
  - icon: 💾
    title: 静默自动保存
    details: 输入停顿后自动写盘,失焦、切后台、关页面都会兜底保存。没有保存按钮,不用记得手动保存。
  - icon: ✨
    title: 极简无按钮
    details: 整个页面只有一个文本框,全靠 URL 控制。手机上打开即用,复制粘贴顺手。
---
