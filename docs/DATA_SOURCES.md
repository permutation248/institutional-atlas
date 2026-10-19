# 美国组织及经济数据：官方来源索引

**优先级：政府/组织官方职责页与法定文件 > 官方开放数据 API > 官方年度报告 > 受权整合平台 > 非官方报道。** 任何“当前领导人”必须优先使用机构现行领导页面，不沿用数年前的提名名单。

## A. 联邦顶层机构（首先执行）

| 平台 | 地址 | 作用和限制 |
|---|---|---|
| USAGov 三大分支 | https://www.usa.gov/branches-of-government | 联邦行政、立法和司法结构 |
| USAGov 机构 A-Z | https://www.usa.gov/agency-index/ | 机构官网、简介和联系方式 |
| United States Government Manual | https://usgovernmentmanual.gov/About | 机构职责、历史、领导、下属单位 |
| SAM.gov FH Public API | https://open.gsa.gov/api/fh-public-api/ | 官方部门和第二层 SubTier；非联邦账号默认 10 请求/天，需 API key |
| USAspending Agency API | https://api.usaspending.gov/docs/endpoints/federal_accounts/ | 财政账户、支出承诺和下属机构统计；不能用所有字段解释组织层级 |
| 官方 Cabinet 页面 | https://www.whitehouse.gov/administration/cabinet/ | 行政部门负责人索引，但须进一步验证最新人员变化 |

**特别警告：** SAM.gov `FH FOUO API` 为受限制数据，官方明确不允许将其用于公开展示完整政府层级（https://open.gsa.gov/api/fh-fouo-api/）。此项目不能使用它。只使用 FH Public API 或其他允许公开传播的官方资料。

## B. 机构规模与职能

| 源 | 地址 |
|---|---|
| 美国财政部内设局 | https://home.treasury.gov/about/bureaus/ |
| 美国卫生部机构目录 | https://www.hhs.gov/about/organization/divisions/index.html |
| 美国商务部局室 | https://www.commerce.gov/bureaus-and-offices |
| NSF 组织与领导 | https://www.nsf.gov/about/leadership |
| NIH 组织与领导 | https://www.nih.gov/about-nih/organization/nih-leadership |
| 美国联邦政府就业数据 | https://www.opm.gov/data/ （按最新可用公开统计源核验） |
| 美国州和地方公务部门人数 | https://www.census.gov/data/developers/data-sets/govsemp.html |

## C. 经济与资金（第二阶段）

| 源 | 地址 | 注意事项 |
|---|---|---|
| USAspending | https://api.usaspending.gov/ | obligations/outlays 不同；授予不是上下级 |
| Grants.gov | https://www.grants.gov/api/api-guide | 资助机会不代表已实际拨款 |
| NIH RePORTER | https://api.reporter.nih.gov/ | 医学研究奖励、执行单位、资金 |
| NSF Award Search | https://www.nsf.gov/awardsearch/ | NSF 资助记录，需核验可供程序化查询方式 |
| SEC EDGAR XBRL | https://www.sec.gov/search-filings/edgar-application-programming-interfaces | 上市企业财务和子公司，访问限速 |
| GLEIF | https://www.gleif.org/en/lei-data/gleif-api/ | 法人身份及部分会计并表关系，不是完整股权穿透 |
| OpenAlex | https://developers.openalex.org/ | 科研机构、资助、论文及项目关联，需区分来源精度 |

## D. 当前示范的大学、公司、银行

- UC campuses： https://www.universityofcalifornia.edu/about-uc/campuses-locations
- UC leadership： https://www.universityofcalifornia.edu/about-uc/leadership
- Alphabet SEC 2025 subsidiaries： https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/googexhibit2101q42025.htm
- Bank of America subsidiaries： https://investor.bankofamerica.com/regulatory-and-other-filings/subsidiary-and-country-disclosures?force_isolation=true

## 采集的四种方式

1. 有官方 JSON/CSV/API：优先使用稳定 API，分页、缓存、遵循限速；API key 只留本地环境变量。
2. 无官方 API 但可合法下载：存来源 URL、发布日、文件校验值；做可重复处理。
3. 只有公开网页：先人工核验；尊重 robots.txt/使用条款、访问频率和登录限制，不采用规避访问控制技术。
4. PDF/图片组织图：提取为候选结构，需人工或者交叉官方文本核验；LLM 不能自行发布未经核对的关系。

## 更新建议

机构存在/隶属：每月或遇结构调整检查；核心负责人：每周检查且保留任期历史；机构公开公告：按官方 RSS/页面更新；财务指标：按报告周期，不将未更新报告认作实时金额。

## 2026-10-19 本地化迭代

本轮实际打开的官方正文、25 个新增节点的证据、现任名录与冲突，统一记录在 [RESEARCH_2026-10-19.md](RESEARCH_2026-10-19.md)。上述通用 API 索引属于后续接入线索，本轮未调用所有列出接口，也未获取 SAM.gov API key。当前事实仍由 Markdown 维护，不含后台自动采集。
