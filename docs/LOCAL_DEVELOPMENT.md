# 本地开发与 GitHub 同步

## 本地目录边界

```text
组织结构世界模型/
├── institutional-atlas/     # 本仓库；源码、事实、公开文档与生成页面
└── project-context/         # 仅本地；原聊天、原包、想法、开发记录
```

Git 根目录只位于 `institutional-atlas/`。不要在共同父目录再初始化 Git。`project-context/` 不是靠忽略规则隐藏的仓库子目录，而是位于仓库之外。

仓库远端为 <https://github.com/permutation248/institutional-atlas>，分支 `main`，SSH 地址为 `git@github.com:permutation248/institutional-atlas.git`。

## 运行与更新

按照 README 安装项目内虚拟环境。`scripts/dev.sh check` 执行构建和测试；`scripts/dev.sh serve` 构建后启动本机预览。macOS 用户可双击根目录 `启动图谱.command`。直接双击 `dist/index.html` 适合不需要开发服务器的离线浏览。

事实更新顺序：阅读原始官方页面 → 编辑 Markdown → 保留来源和准确日期 → 构建 → 测试 → 浏览器刷新检查 → 检查 diff → commit → push。

- `verified_at` 是档案来源声明的核验日期；继承记录不自动算本轮研究。
- `research_reviewed_at` 标识本轮实际读取官方正文的复核日期；`research_notes` 说明复核范围和缺口。
- 公开报告将“字段已有值”“结构校验通过”与“已阅读当前官方来源”分开。
- 原始数据有冲突时保留变更说明，不从网页无法访问推断机构不存在。
- 构建产物随代码提交，克隆后无需安装依赖即可打开 HTML。

## 日常同步

```bash
git status
git pull --ff-only
scripts/dev.sh check
git diff
# 明确选择需要公开的项目文件，再提交和推送。
git add data docs web scripts tests dist README.md
git commit -m "Update source-backed institution records"
git push
```

首次 SSH 认证或网络失败时，先解决 Git 的实际错误；不要自动更换账户、改权限或把密钥写入项目。个人研究笔记继续写入同级 `project-context/`。

## 本轮验证边界

本地测试验证结构、字段、生成逻辑及浏览器交互；CI 不会自动判定一个 URL 的正文支持某条事实。自动覆盖统计也不是全网完整性或事实真实性的证明。

下一轮从 `docs/COVERAGE.md` 的未覆盖目录开始，遵循 `AGENTS.md` 的证据要求。公开服务、自动采集、数据库和 AI 分析需要独立实现与验收，不属于当前静态图谱的既有能力。
