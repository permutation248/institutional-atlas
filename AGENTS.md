# Codex Working Instructions: Institutional Atlas

你正在改造一个 **evidence-first、Markdown-first 的组织依赖图谱**，请先阅读 `VISION.md`、`docs/ONTOLOGY.md`、`docs/DATA_MODEL.md`、`docs/ROADMAP.md`。必须执行下列要求：

1. **自上而下研究美国联邦政府**：先三大分支、15 个行政部门和独立机构，再逐层展开；后续扩展公司、大学、银行。优先补全广度，再深入关键子树。
2. **只加结构强边**：`PART_OF`, `REPORTS_TO`, `CONTROLLED_BY`, `FUNCTION_DELEGATED_BY`, `FINANCIALLY_DEPENDENT_ON`。不得把普通拨款、监管、合同、合作、竞争、新闻共现当强结构边。
3. **组织层级不是简单法律所有权**：国家仅用于导航定位，美国联邦与州/市不是同一条行政汇报链。不能把最高法院或国会画成总统下属。
4. **每个组织尽量填满字段**：职责、官网、现任领导（姓名/准确头衔/代理或空缺）、外部公告、员工规模（年度/口径）、内设机构、预算/支出数据（明确会计口径）。若无法证实，显式 `null` 或 `[]`，绝不编造。
5. **官方来源优先**：新节点和新边须有可打开的官方页面证据。网页检索结果只作为线索，必须阅读原始官方页面的正文后才把事实写入 YAML。务必区分采集日、来源发布日、事实生效日。
6. **当最新信息与既有示例冲突时**：保留来源，优先官方最近更新的职务/结构，生成冲突日志；不无证据地覆盖数据。
7. **美国组织特殊情况**：`Department of War` 是 2025 年公布的 Department of Defense 次级名称（请核验最新法规）；NSF 现行页面称主任职位空缺、Brian Stone 履行主任职责，不得错误地写成正式主任。
8. **联网与使用许可**：只访问官方公开 API、许可允许下载的内容。不要使用美国 SAM.gov `FH FOUO API` 构造公共组织关系，不要尝试绕过访问限制。
9. **本地事实唯一来源为 Markdown**：`data/entities/{domain}/{id}.md`。不可手工直接改 `dist/atlas.json` 或生成的 `dist/index.html`；改 Markdown 或 `web/*`，运行构建脚本。
10. **每次迭代必须测试**：`python scripts/build.py` 和 `python -m unittest discover -s tests -v`。检查 HTML 能离线打开且官网/来源是 HTTPS。
11. **工作总结**：报告新增节点数、边数、完成层级、负责人覆盖率、新增源网站、数据缺失和未核验冲突；附 3-5 条可以点击的示例路径。
12. **严格区分财务**：预算授权、拨款、obligation、outlay、合同金额、确认收入和净利润完全不同。未经证实不生成数字。不得从公开资助推断学校/企业完全受政府控制。

如联网不可用，优先整理已给示范数据、实现前端及检验逻辑，并将需要核实的条目放入 `docs/COVERAGE.md`；禁止声称自己已经联网核查。
