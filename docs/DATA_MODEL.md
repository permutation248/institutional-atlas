# 组织世界模型数据规范（v0.3）

逐项研究的组织使用 `data/entities/{domain}/{id}.md`。**研究档案、事件和金融机制以 YAML frontmatter 为结构化事实来源；Markdown 正文仅用于人类叙述。** 官方完整名录从带 SHA-256 的原始快照导入 `data/catalogs/`，见下方目录层规范。 `scripts/build.py` 验证 ID、官网、引用、边类型、父节点存在性及环依赖，并生成单文件 HTML。地理州界属于有许可、带版本与哈希的外部地图素材，来源见 [MAP_SOURCES.md](MAP_SOURCES.md)。

```yaml
---
id: us-nih
name: National Institutes of Health
name_zh: 美国国立卫生研究院
category: executive_agency
jurisdiction: US
domain: government
official_url: https://www.nih.gov/
website_type: official
function: 生物医学和公共卫生研究
leader:
  name: Jay Bhattacharya
  title: NIH Director
  status: confirmed
  as_of: '2026-10-19'
  evidence_url: https://www.nih.gov/about-nih/organization/nih-leadership
employee_count: null
financial_profile: []
publications:
  - label: NIH News Releases
    url: https://www.nih.gov/news-events/news-releases
parents:
  - parent_id: us-hhs
    type: PART_OF
    evidence_url: https://www.hhs.gov/about/organization/divisions/index.html
    note: HHS 所属运营机构
sources:
  - url: https://www.hhs.gov/about/organization/divisions/index.html
    description: HHS 机构组成
  - url: https://www.nih.gov/about-nih/organization/nih-leadership
    description: NIH 领导名单
verified_at: '2026-10-19'
verification_status: verified
---

# 美国国立卫生研究院

## 本机构承担什么功能？

...
```

### 可空字段

`leader: null` 表示**未核实或不能用一个自然人表示负责人**，不代表职务空缺。正式空缺须标记：

```yaml
leader:
  name: Brian Stone
  title: Chief of Staff, Performing the Duties of NSF Director
  status: performing_duties
  formal_position: 'NSF Director: vacant'
  as_of: '2026-10-19'
  evidence_url: https://www.nsf.gov/about/leadership
```

`employee_count: null` 表示未核验。只在查明口径时填写：

```yaml
employee_count:
  value: 266800
  unit: faculty_and_staff
  period: 'website snapshot, 2026'
  evidence_url: https://www.universityofcalifornia.edu/about-uc
```

`official_url` 必须附组织官网；没有机构专属官网时可使用合法对应的集团/政府门户 URL，但必须用 `website_type: shared_group_site | government_portal | group_customer_site` 标注，不能伪称专属官网。

### 未来的财务字段

```yaml
financial_profile:
  - metric: obligation
    value: 123456
    currency: USD
    fiscal_year: 2025
    scope: federal_awards_for_this_agency
    source_url: https://example.gov/evidence
    source_date: '2026-01-01'
```

**这是纯粹的数据结构示例，数额和 URL 都是占位，不得写入真实实体档案。**

### 推进本体改动的要求

不能因为输入源没有数据就猜。特别是员工人数、单位资产、负责人的任期、新设组织和当前名字可能随时间变化。升级数据模型时同步更新脚本校验、HTML、样例和测试。

## 本地化版本的复核记录

`research_reviewed_at` 为本轮实际阅读官方正文的日期，`research_notes` 说明核验范围及未完成字段。继承的 `verified_at` 不能自动算作本轮复核。负责人 `status: serving` 表示现行官网列示现任姓名/头衔，未独立核对确认程序；`confirmed`、`acting`、`performing_duties`、`vacant`、`unknown` 等分别保留其含义。`leader: null` 与正式职位空缺不同。

构建产物 `dist/coverage.json` 统计字段有无记录、继承与本轮局部复核数量，不执行网络事实核验。新增关系的时间及额外证据字段会原样保留到 JSON；字段类型、合法日期、重复 ID/边、引用、关系环和财务口径由构建程序检查。

## 持续资金依赖边的附加证据

当前数据集没有资金依赖边。未来添加 `FINANCIALLY_DEPENDENT_ON` 时，必须为 `periods` 中每个年度分别提供 `year`、`funding_share`、`numerator`、`denominator`、`currency`、`scope` 和 `evidence_url`；至少两个连续年度、同币种及可比口径，分子/分母须与比例一致且每年均大于 0.5。逐年比例是校验依据；可选的边级 `funding_share` 只能作为摘要，不替代逐年证据。这个门槛是当前版本的工程约定，需要修改时同步更新本体、校验和测试；它不是法定依赖标准，也不能从单笔合同推导。

## 地理、使命、治理与资金组织方式

以下属性可省略或为 `null`，表示尚未核验。存在时须完整填写指定字段，不能用空字符串或 `0` 冒充未知：

| 属性 | 字段与含义 |
| --- | --- |
| `location` | `lat`、`lon` 为有限数字，分别位于 −90…90、−180…180；`city`、`state` 标注地点；`precision` 为 `city`、`campus` 或 `headquarters`；`evidence_url` 是官方位置证据。 |
| `mission` | 组织愿景或稳定使命的非空文字；依据组织官网，不推断真实动机。 |
| `ecosystem_role` | 组织在社会、产业、科研或金融体系中的作用；避免用分析性比喻替代法定从属。 |
| `governance` | `apex` 是正式最高权威或决策机关；`mechanism` 说明授权、表决、任命、监督等如何形成有效决定；`evidence_url` 指向章程或治理证据。 |
| `funding_model` | `summary` 总述；`inflows`、`outflows` 为文字列表；`evidence_url` 指向官方预算、年报或运作说明。这里解释机制，不含未经核验的金额。 |

`governance.apex` 可以是董事会、受托人会、董事会与校长的分工或国会两院等，不能强行化约为一个自然人。它与 `leader` 的公开任职资料互补。`governance.mechanism` 表示可观察的制度决策程序；“达成有效决定”不等于全体一致或没有分歧。

位置证据可以证明机构位于某个城市或校园，而坐标采用近似中心。此时用 `precision: city` 或 `campus`，在 `research_notes` 中说明近似程度。地图不展示个人住址，也不将近似坐标说成实测入口位置。

## 官方事件卡片

事件存放于 `data/events/{id}.md`，与组织和强结构边分开：

```yaml
id: example-official-release
title: 公告标题
summary: 来源实际表述的事实摘要
date: '2026-10-23'
entity_ids: [existing-organization-id]
category: research
source_url: https://example.gov/news/release
source_name: 官方新闻室
reviewed_at: '2026-10-24'
```

这是结构示例，不是真实公告。`date` 是来源的发布日，不能晚于实际阅读日期 `reviewed_at`。公告提到的未来活动可以用额外字段 `scheduled_for` 记录，不能将未来计划写成已发生的事件。`entity_ids` 至少指向一个已存在的组织，不允许悬空或重复引用；概念性经济部门不能作为具体新闻机构。页面标记“最近收录”时必须显示实际日期，不能把归档公告说成今日新闻或实时推送。

## 资金机制覆盖层

记录位于 `data/flows/{id}.md`：

```yaml
id: example-financial-mechanism
source_id: households
target_id: existing-organization-id
label: 税收
kind: tax
description: 基于官方证据解释资金如何经过这一环节；非某笔实际支付。
evidence_url: https://example.gov/taxes
as_of: '2026-10-24'
basis: mechanism
amount: null
```

这是结构示例。该层用方向表达资金或制度性资源的运作方向，**不会生成 `PART_OF`、`CONTROLLED_BY` 或 `FINANCIALLY_DEPENDENT_ON` 边**。`basis` 当前只允许 `mechanism`，`amount` 必须显式为 `null`。动画速度、线条宽度和颜色不代表金额。未来如果收录实际支付或证券交易，须另行设计时间、会计口径、币种、证据与金额的完整量化模型。

端点可以是现有组织 ID，或以下概念性部门：`households`（家庭与个人）、`businesses`（企业部门）、`investors`（投资者）、`banks`（银行体系）、`universities`（大学部门）、`capital-markets`（资本市场）、`federal-budget`（联邦预算体系）。这些说明性节点由构建器输出至 `graph.sectors`，不算作组织、不进入层级、不能冒充法人。流转不能自指；相同起点、终点、类型与标签不得重复收录。

## 构建与覆盖统计

生成的 `graph` 包含 `entities`、`edges`、`events`、`flows`、`sectors`、`geography` 六个独立集合。组织仍可存在多个独立子图；资金覆盖层可以连接它们，但不改变正式隶属关系。所有集合的稳定 ID 不能冲突。事件按发布日倒序输出。

测试使用临时数据目录时，补充数据只从该目录同级的 `events`、`flows`、`geography` 读取；缺失目录表示空层，不会偷用正式项目数据。构建检查实体位置与治理字段、新闻引用/日期/URL、资金端点与机制口径，以及地图数据哈希。`coverage.json` 增加位置、使命、生态作用、治理与资金组织方式的字段覆盖量，以及事件、机制和州界数量。

`metadata.snapshot_date` 是本地记录的最近核验/收录日期，不是构建执行时间。`network_verification_performed: false` 表示构建程序没有联网检查来源；人工采集行为仍由每份记录的来源和日期说明。


## v0.3 完整目录层

`data/catalogs/*.json` 由三份 `scripts/import_*.py` 从原始快照复建，包含 metadata 与 records。metadata 必须给出来源、采集日、期间、范围、排除项、原始文件路径及 SHA-256。构建仅校验本地快照，不自动联网更新。

目录记录用 `record_kind: directory`，可缺少官网、位置、职责、负责人、治理和财务；`verified_at: null`，`catalog_records.retrieved_at` 是采集日期而非逐项核验日期。只有精确 `curated_id` 可合并研究档案，冲突稳定编号会阻止构建。`source_fields` 保留源目录的原始字段，不自动转换为现行关系或 HTTPS 事实。

`data/catalog-links.json` 记录明确核验的跨目录同一身份；合并保留全部目录来源和标识，不依名称相似自动合并。发行人名录按明确名称归并证券，并保留各 ticker/exchange，但没有 CIK 时不能视为唯一法人目录。官方来源中的未知、历史记录和未处理重复均应在覆盖说明中可见。
