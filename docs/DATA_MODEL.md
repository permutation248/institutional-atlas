# Markdown 组织档案规范（v0.1）

每个组织是 `data/entities/{domain}/{id}.md`。**YAML frontmatter 是结构化事实唯一来源；Markdown 正文仅用于人类叙述。** `scripts/build.py` 验证 ID、官网、引用、边类型、父节点存在性及环依赖，并生成单文件 HTML。

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
