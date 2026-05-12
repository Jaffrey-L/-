# AI Daily Radar

一个面向 AI 前沿资讯的日报网页模板，覆盖：

- 核心 AI 公司新闻
- 核心 AI 博主观点
- AI 个人公司大神动态
- Vibe Coding / Prompt / Agent 实战专区

## 本地启动

直接双击 `index.html` 即可查看静态页面。

如果浏览器本地 `file://` 无法读取 `sources.json`，可在目录里启动一个静态服务，例如：

```powershell
cd D:\知识地图\AI最新新消息播报
python -m http.server 8000
```

然后访问 `http://localhost:8000`。

## 文件说明

- `index.html`：页面结构
- `styles.css`：视觉样式
- `app.js`：渲染逻辑、筛选逻辑、示例日报数据
- `sources.json`：来源池白名单（可持续维护）

## 后续扩展建议

1. 接入 RSS/API：把 `sampleNews` 替换为自动抓取结果。
2. 增加“去重逻辑”：同事件保留 A 级首发。
3. 增加“企业应用优先”打分：让企业落地新闻自然置顶。
4. 增加归档：每日生成一份 `YYYY-MM-DD.json` 便于追溯。

## GitHub 与部署

1. 创建 GitHub 仓库后，把本地仓库关联并推送：

```powershell
cd D:\知识地图\AI最新新消息播报
git branch -M main
git remote add origin <你的仓库地址>
git push -u origin main
```

2. 在 GitHub 仓库设置中开启 Pages：
- `Settings` -> `Pages` -> `Build and deployment`
- Source 选择 `GitHub Actions`

3. 推送到 `main` 后会自动触发 `.github/workflows/deploy-gh-pages.yml` 完成发布。
