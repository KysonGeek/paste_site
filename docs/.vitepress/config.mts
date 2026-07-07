import { defineConfig } from 'vitepress'

export default defineConfig({
  lang: 'zh-CN',
  title: 'paste',
  description: '极简文本中转站 — 访问 /任意名字 打开全屏文本框,内容变动时自动保存。',

  // GitHub Pages 项目站点部署在 /<repo>/ 子路径下
  base: '/paste_site/',

  themeConfig: {
    nav: [
      { text: '快速开始', link: '/guide/getting-started' },
      { text: '工作原理', link: '/guide/how-it-works' },
      { text: '部署', link: '/deploy' },
      { text: 'GitHub', link: 'https://github.com/KysonGeek/paste_site' }
    ],

    sidebar: {
      '/guide/': [
        {
          text: '指南',
          items: [
            { text: '快速开始', link: '/guide/getting-started' },
            { text: '工作原理', link: '/guide/how-it-works' }
          ]
        },
        {
          text: '运维',
          items: [{ text: '部署', link: '/deploy' }]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/KysonGeek/paste_site' }
    ],

    docFooter: {
      prev: '上一页',
      next: '下一页'
    },

    outline: { label: '本页目录' },
    returnToTopLabel: '回到顶部',
    darkModeSwitchLabel: '主题',
    lightModeSwitchTitle: '切换到浅色模式',
    darkModeSwitchTitle: '切换到深色模式'
  }
})
