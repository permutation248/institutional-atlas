# 政府治理、近期事件与金融机制研究记录

复核日期：2026-10-24。此记录配合“组织视觉模型”的美国首版，范围是政府机构数据、事件卡片与资金／政策机制层。官网正文和官方目录均在本轮实际读取；记录内的 `evidence_url`、`sources` 和日期可回溯到对应证据。

## 覆盖与数据语义

本轮新增 12 个政府组织，并增强 30 个原有政府记录。政府域共有 71 个组织，35 个提供城市级地图定位；15 个内阁部门均具备使命、生态定位、治理和财政机制说明。三权分支等抽象集合不伪造总部，地图尚未覆盖所有下属局、分支机构与所有法院。

新组织：SEC、FDIC、CFPB、CFTC、FTC、FCC、GAO、CBO、OMB、哥伦比亚特区联邦巡回上诉法院、哥伦比亚特区联邦地区法院、美国法院行政办公室。两个法院是具体实例，不代表全国法院已穷尽。

- 立法：Congress → House / Senate；GAO 与 CBO 属于立法分支的监督或分析支持机构。
- 行政：15 个内阁部门与独立机构；财政部已有 IRS、Fiscal Service 等业务局。
- 司法：最高法院、两个具体下级法院，以及法院行政支持机构。行政办公室的服务职责不等于有权决定案件结果。
- CFPB 同时记录行政机构范围与 Federal Reserve System 内独立局身份，不把它简化为 Board of Governors 的普通内设部门。依据为[联储官方结构说明](https://www.federalreservehistory.org/essays/fed-structure)，资金转移单独进入机制层。

`governance.apex` 表达最终制度权威或负责职位；`mechanism` 表达如何形成可执行决定。“收敛”不是所有人形成同一意见：法院以程序、审议和裁判结案，委员会通过议程和表决，行政部门依职权及授权流程行动，国会需经过两院与成法程序。模型不将全体联邦政府归为一名“CEO”。[美国政府三分支](https://www.usa.gov/branches-of-government)、[内阁制度](https://www.whitehouse.gov/government/executive-branch/)、[司法行政](https://www.uscourts.gov/administration-policies/judicial-administration)支撑这些区分。

## 地图与负责人

全部新增政府坐标使用 `precision: city`，是人工设定的城市近似点，不是建筑入口或测绘结果；地点证据是官方联系信息或组织所在地。政府域的多个 Washington 点有意共用城市中心，地图应使用聚合，而非制造看似精确的错位地址。

五角大楼以 Arlington, Virginia 为物理城市：白宫[行政分支说明](https://www.whitehouse.gov/government/executive-branch/)确认国防部总部，当前 [USAJOBS 官方地点](https://www.usajobs.gov/job/851939900)确认 Arlington；没有把 Washington 邮寄地址当作物理位置。国务院使用[现行官方外交导览](https://stories.state.gov/diplomacy-walking-tour/)，VA 使用[中央办公楼官方记录](https://department.va.gov/history/va-central-office-building-a-legacy-of-service-to-veterans-since-1918/)。

本轮重新读取[现行 Cabinet 名录](https://www.whitehouse.gov/administration/cabinet/)，15 个部门负责人的 `as_of` 更新为 2026-10-24；现任名录核实不自动等同穷尽所有任命法律程序。CFPB 的 Mark Paoletta、CBO 的 Phillip L. Swagel、CFTC 的 Michael S. Selig、两家法院的首席法官及 Fiscal Service 的 Joseph Gioeli 均依据相应当前官网。未验证的机构负责人保留 `null`。`verified_at` 的旧值不会被解释为所有字段当日重新核验，局部复核使用 `research_reviewed_at` 和字段日期。

## 金融机制层

18 条记录位于 `data/flows/`，均为 `basis: mechanism`、`amount: null`。这是一组制度与经济流转路径，既不是实测交易网络，也不是把箭头画成金额规模。`households`、`businesses`、`investors`、`banks`、`universities`、`capital-markets`、`federal-budget` 是概念部门，不是新增组织。

| 机制段 | 核验依据 | 解读边界 |
| --- | --- | --- |
| 家庭／企业 → IRS → Treasury | [IRS 职责](https://www.irs.gov/about-irs/the-agency-its-mission-and-statutory-authority)、[Treasury 职责](https://home.treasury.gov/about/general-information/role-of-the-treasury) | 表达税务管理与政府收入职能，不表示逐笔款项必须经图中每个法人账户 |
| 投资者 → Treasury → 投资者 | [国债价格与利息](https://www.treasurydirect.gov/marketable-securities/understanding-pricing/)、[Fiscal Service](https://fiscal.treasury.gov/about-us) | 发行融资与本息偿付；区分一级发行和二级交易 |
| Congress → 财政预算 → NSF → 大学部门 | [预算程序](https://www.usa.gov/federal-budget-process)、[NSF 预算](https://www.nsf.gov/about/budget)、[NSF](https://www.nsf.gov/about) | 国会预算权不是现金；预算请求、拨款和实际支出不同；没有推断每所大学均获得指定资助 |
| Fed / FOMC / NY Fed → 银行或市场 | [纽约联储货币政策实施](https://www.newyorkfed.org/markets/domestic-market-operations/monetary-policy-implementation) | 区分政策决定、利率工具和市场执行；不把政策指令当资金转账 |
| 存款、信贷、发行融资与分红 | [FFIEC 机构类型](https://www.ffiec.gov/npw/Help/InstitutionTypes)、[NCUA 账户说明](https://mycreditunion.gov/brochure-publications/brochure/money-basics-guide-savings-and-checking-accounts)、[SEC 投资者教育](https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks) | 存款不是银行股权；股票换手不是全部给发行人新增资金；分红非保证 |
| 联储 → CFPB；受保银行 → FDIC | [CFPB 转移请求](https://www.consumerfinance.gov/about-us/budget-strategy/funds-transfer-requests/)、FDIC 记录所列政府手册 | 资金机制不升级为控制边；FDIC 的历史来源限制见下 |

15 个行政部门的 `funding_model` 说明一般财政框架及职责方向，未填造每个项目的预算数字、贷款保证损失或实际支付。Treasury 自身运营预算与其管理的全政府现金流明确区分。

## 近期官方事件

14 张卡片的官方发布日期均在 2026-09-17 至 2026-10-22，复核日为 2026-10-24。每条保留原文链接、发布来源、关联组织、简短说明与日期。它们是精选官方发布快照，未宣称全天候新闻抓取。组织点上的事件标志表示“关联组织所在地”，不表示事件发生现场。

| 官方发布日期 | 记录 | 原文 |
| --- | --- | --- |
| 2026-10-22 | 财政部公布对外投资安全规则提案 | [U.S. Treasury](https://home.treasury.gov/news/press-releases/sb0667/) |
| 2026-10-22 | FTC 对涉嫌冒充政府的护照服务提起诉讼 | [FTC](https://www.ftc.gov/news-events/news/press-releases/2026/10/ftc-sues-perpetrators-government-impersonation-scheme-over-deceptive-ads-misleading-promises-fake) |
| 2026-10-19 | FinCEN 移送学生援助可疑交易线索 | [U.S. Treasury](https://home.treasury.gov/news/press-releases/sb0663/) |
| 2026-10-16 | NIST 报告芯片级光学频率梳研究进展 | [NIST](https://www.nist.gov/news-events/news/2026/10/new-chip-based-tape-measure-light-could-revolutionize-mobile-timekeeping) |
| 2026-10-15 | FTC 向沃尔玛汇款服务案受影响消费者退款 | [FTC](https://www.ftc.gov/news-events/news/press-releases/2026/10/ftc-sends-more-98-million-consumers-harmed-walmarts-failure-stop-scammers-used-its-wire-transfer) |
| 2026-10-14 | SEC 公布 IPO 与众筹讨论议程 | [SEC](https://www.sec.gov/newsroom/press-releases/2026-105-sec-small-business-advisory-committee-discuss-ipo-modernization-regulation-crowdfunding) |
| 2026-10-09 | 布朗大学公布 FY2026 捐赠基金回报与支出 | [Brown University](https://www.brown.edu/news/2026-10-09/brown-endowment-return-2026) |
| 2026-10-08 | NSF 宣布元科学与新科研资助机制 | [NSF](https://www.nsf.gov/news/nsf-lays-foundation-next-generation-technologies-support) |
| 2026-10-07 | 联储发布九月 FOMC 会议纪要 | [Federal Reserve](https://www.federalreserve.gov/newsevents/pressreleases/monetary20261007a.htm) |
| 2026-10-02 | 特斯拉发布第三季度交付与储能部署数据 | [Tesla Investor Relations](https://ir.tesla.com/press-release/tesla-third-quarter-2026-production-deliveries-and-deployments) |
| 2026-09-30 | 联储完成压力测试透明度规则修订 | [Federal Reserve](https://www.federalreserve.gov/newsevents/pressreleases/bcreg20260930a.htm) |
| 2026-09-29 | 联储与 FDIC 发布银行处置计划反馈 | [Federal Reserve / FDIC](https://www.federalreserve.gov/newsevents/pressreleases/bcreg20260929a.htm) |
| 2026-09-18 | NIST 授予跨八州的网络安全人才合作协议 | [NIST](https://www.nist.gov/news-events/news/2026/09/nist-awards-more-17-million-support-cybersecurity-workforce-development) |
| 2026-09-17 | NSF ELEGANT 推动半导体研究走向制造 | [NSF](https://www.nsf.gov/news/nsf-invests-translating-low-dimensional-semiconductor) |

特别处理：SEC 的 10 月 14 日发布是对 10 月 27 日会议的预告，未写成会议已经发生；FOMC 的 10 月 7 日是纪要发布日期，会议实际为 9 月 15–16 日；Treasury 对外投资规则标为提案；FTC 起诉描述为指控而非司法认定；FinCEN 涉嫌活动金额不等同已经证明的损失；Brown 的投资回报率与对运营的分配额分别说明；Tesla 使用原发布正文的 10 月 2 日，而非 IR 首页另一个 10 月 21 日标签。

## 来源限制与后续维护

- FDIC 主站多个页面返回 403。本轮采用 USA.gov 当前机构入口、9 月 29 日 Fed/FDIC 联合发布和政府手册的稳定制度说明。手册人员表为历史资料，未用其旧人名、人数、保险覆盖数字或金额推断 2026 状态；该节点保持 `partial`。后续应补当期 FDIC 董事会和年度财报原文。
- FCC 主站部分页不可读取；使用 USA.gov 与[CRS R45699](https://www.congress.gov/crs-product/R45699)的制度说明，未填现任主席人名。制度席位数不等于实际在任人数。
- 当期机构目录可以证实机构职能和城市，但不会自动证明全部下属组织、完整预算和所有政策变动。未知处保持空值。
- 读取正文并不等于永久保存网页快照；本目录保留整理后的可版本化上下文及出处。新闻原文会变更或下线，应继续以字段级日期维护。
- 资金层当前没有量化金额，未来接入 USAspending、官方财报或财政数据时应另建可区分“预算／承诺／支付”的记录，不能直接把本轮机制箭头当测量值。

## 本轮验证

`python scripts/build.py` 和 `python -m unittest discover -s tests -v` 用于验证数据引用、日期、来源字段及构建结果；它们不能替代事实来源复核。本次构建确认 132 个组织、90 条结构边、14 个事件、18 条金融机制、93 个地图定位；45 项测试全部通过。
