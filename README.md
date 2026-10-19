# Institutional Atlas · 从组织结构理解世界

以组织为节点，以正式组成、负责、控制、职能授权和经过证明的持续资金依赖为边，自上而下探索社会的组织结构。首个案例是美国联邦政府；金融、企业和大学使用同一套模型。

这是一个 **Markdown 驱动、证据可追溯、可离线浏览** 的研究原型。普通合作、竞争、监管和一笔资助不会自动变成组织隶属关系。不同领域保留独立入口。

![Institutional Atlas 本地原型](preview.jpg)

## 直接使用

双击 [`dist/index.html`](dist/index.html)，即可离线打开图谱，无需数据库、Node、API key 或第三方 CDN。

支持：四个领域切换、中英文搜索、组织下钻、上一级与面包屑导航、缩放、官网与证据跳转、领导任职状态、人员和财务资料、JSON 导出、通过 `#机构ID` 定位档案。

在 macOS 也可双击 `启动图谱.command` 启动开发预览。终端开发方式见下文。

## 本地开发

需要 Python 3.9 或更高版本。依赖安装到项目虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/build.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory dist
```

浏览器打开 <http://127.0.0.1:8765>。源码修改后重新构建并刷新页面。服务器只提供 `dist/`，并只监听本机；同级本地研究资料不在服务目录中。

## 数据范围与可信度

当前 **76 个节点、72 条关系**，比原始项目新增 25 个政府节点与对应关系。本地化版本核验美国政府顶层与优先子树，扩展 Treasury、HHS、Commerce 和部分独立机构。最新数字见 [`docs/COVERAGE.md`](docs/COVERAGE.md) 和自动生成的 [`dist/coverage.json`](dist/coverage.json)。

- 美国政府：联邦三大分支、15 个行政部门、国会两院、最高法院，以及部分部门内设机构与独立机构。
- 高校：加州大学系统及十个校区。
- 企业：Alphabet 与三个 SEC 披露的代表性子公司。
- 金融：Bank of America Corporation 与 Bank of America, N.A.。

**这不是完整美国组织名录，也不是实时财务数据库。** 人数、财务和领导字段允许缺失，未知不等于零。原包记录与本轮官方来源复核在界面中分别标示；“本轮复核”也不代表所有字段都已完整确认。具体核验范围、冲突和无法访问的来源见 [`docs/RESEARCH_2026-10-19.md`](docs/RESEARCH_2026-10-19.md)。

## 编辑组织与关系

唯一人工事实来源为 `data/entities/{domain}/{id}.md`。修改 YAML frontmatter，构建程序会校验并生成 JSON、覆盖统计和独立 HTML。不要直接手改 `dist/`。

每个组织尽量记录职责、官网、准确的领导岗位及任职状态、公告入口、人员统计口径、内部组成、财务指标与原始证据。每条关系都独立附官方来源。关系以“子组织 → 上级/依赖对象”存储，页面自上而下展示导航方向。详细字段见 [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)，语义见 [`docs/ONTOLOGY.md`](docs/ONTOLOGY.md)。

国家是导航范围，不能因处于同一国家就添加上下级关系。国会与最高法院不向总统汇报，州政府不是联邦普通下属部门，大学取得科研拨款也不会因此成为资助机构的下属。

## 目录

```text
institutional-atlas/
├── AGENTS.md / CODEX_TASK.md  # 继续开发的规范与任务
├── VISION.md                 # 长期方向
├── data/entities/            # 一组织一份 Markdown
├── docs/                     # 本体、数据规范、来源、覆盖与路线
├── scripts/                  # 构建与本地开发工具
├── web/                      # HTML / CSS / JavaScript 源码
├── dist/                     # 可离线分发的生成产物
├── tests/                    # 构建与数据校验
└── .github/workflows/        # 自动构建与测试
```

聊天原文、原始压缩包、个人思路和过程记录保存在仓库外的同级 `project-context/`。该目录不参与 Git 同步。公开项目文档仍保留在仓库内，便于他人理解和运行。

## 同步 GitHub

```bash
git pull --ff-only
# 编辑、构建、测试并检查 git diff 后：
git add data docs web scripts tests dist README.md
git commit -m "Describe the verified change"
git push
```

同步是显式的 Git 操作。没有后台自动上传，也不需要把本地聊天或密钥加入仓库。开发流程详见 [`docs/LOCAL_DEVELOPMENT.md`](docs/LOCAL_DEVELOPMENT.md)。

## 下一步

继续完善其余行政部门的公开第二层组织；按字段核验领导、公告、人数与财务口径；建立事实有效期及变更历史。完整路线见 [`docs/ROADMAP.md`](docs/ROADMAP.md)。先建立可核验事实，再探索更广的组织与资源世界模型。

代码采用 [MIT License](LICENSE)。第三方内容与数据源的使用条件分别适用。项目与所示组织无官方隶属或背书关系。
