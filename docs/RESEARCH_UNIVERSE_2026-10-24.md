# 组织视觉模型：大学、企业和金融机构扩展复核

研究日期：2026-10-24。本文记录这一轮组织样本扩展，不代表全美组织普查。

## 范围与结果

新增 44 个实体：20 所大学、2 个公立大学系统、12 家大型企业、10 个金融或中央银行体系实体。原有 UC 系统与 10 校区、Alphabet 与 3 个法律子实体、Bank of America 集团与银行实体共 17 个记录得到补充。三个目录合计 61 个实体；新增 5 条结构边（UT Austin→UT System、Georgia Tech→USG、Fed Board/FOMC/NY Fed→Federal Reserve System）。其他行业或政府新增数由项目总报告汇总。

大学覆盖新英格兰、纽约与中大西洋、中西部、南部、得州、加州和太平洋西北；企业覆盖消费硬件、软件、云服务、半导体、社交平台、汽车能源、零售、工业能源、医药、航空及综合控股。金融覆盖中央银行治理与执行层、商业银行、资本市场和资产管理。

字段覆盖（61 个实体）：

|字段|有记录|
|---|---:|
|location|58/61|
|mission|59/61|
|ecosystem_role|61/61|
|governance|49/61|
|funding_model|28/61|
|leader|14/61|
|publications|61/61|

全部标为 `verification_status: partial`。有字段不等于完成全部细节核验；自然人负责人仅记录官网明确列示者。未知姓名不是职位空缺，`leader: null` 也不表示没有领导者。

## 地图与财务口径

地图使用人工设置的城市级近似经纬度，统一 `precision: city`。证据页核验城市，不宣称地理编码建筑、园区边界或街道门牌。UC Santa Barbara 等校区可位于相邻社区；标记是区域导航。Amazon 同时有 Puget Sound 与 Arlington HQ2，本版选择 Seattle 城市代表点。联储系统分布全美，以 Washington 表示中央治理所在地。Goldman 的 New York City 官方办公地点支持城市定位。

Alphabet Capital US LLC、XXVI Holdings 和 Bank of America, N.A. 暂不落点，避免直接继承母公司地址或 CEO。Google LLC 的法律实体不等同 Google Services/Google Cloud 财务分部。

`funding_model` 是资金组织方式。Harvard、MIT、Brown、UC 系统、UCSF 与 Alphabet 有直接的官方财务分类说明；多数其他企业、银行的流入/流出来自官方业务描述的定性解释，在记录中明确标注为机制推断，不是已核验逐笔交易。没有由机制说明生成交易金额或资金依赖强边。银行存款是负债，资产管理人的客户资产不等于公司自有财产。集团总收入不复制到每个法律子实体。大部分大学独立财务模型仍为未知，不能从公立/私立标签推断收入比例。

本轮没有新增财务金额。UC 2026 问责报告包含 FY2024–25 口径，UCSF Budget 为 2024–25，MIT Facts 财务表为 FY2025；Alphabet 财务释义注明截至 2025-09-30。2026-10-24 是观察日期，不是这些财务事实的发生日期。

## 治理与收敛机制

治理字段描述谁有最终权限，以及通过什么会议、委员会、授权或董事会分工形成决定。大学不是简单 CEO 层级：Harvard 双治理董事会、MIT 教师教育政策决策、UC Regents/President/Academic Senate、州立大学 Regents 等均分别建模。部分企业官网仅提供委员会目录与章程入口，记录明确指出尚未复核具体投票门槛。

Federal Reserve System 是体系容器；Board of Governors、FOMC 和 New York Fed 分别属于体系。FOMC 不画成理事会的单方下属，商业银行也不因受到监管成为联储子公司。研究资助和企业合作不是大学所属关系。

## 当前负责人及冲突处理

本轮官方页面与常见历史认知存在变化，应按页面日期理解，不能回填熟悉的旧姓名：

- [Apple Leadership](https://www.apple.com/leadership/) 当前分别列 John Ternus 为 CEO、Tim Cook 为 Executive Chair，使用前者作为 CEO。不是把旧 CEO 自动延续。
- [Federal Reserve Board 当前名单](https://www.federalreserve.gov/aboutthefed/bios/board/default.htm) 列 Kevin Warsh 为 Chairman。该页为本轮负责人依据，不能将 Jerome Powell 自动延续为现任主席。
- [Columbia 官方介绍](https://www.columbia.edu/content/about-columbia-university) 当前列 Jennifer L. Mnookin 为 President。
- [UC 官方治理页](https://www.universityofcalifornia.edu/about-uc/leadership) 复核 James B. Milliken；系统员工规模沿用此前记录，本轮没有声称重新统计。

Alphabet 首页仍保留创立时期信函，其中职位与业务名称具有历史语境，因此没有将其中 Larry Page 的旧 CEO 叙述作为当前负责人。

## 已知缺口与访问边界

Cornell 官方网站正文访问失败，本版选择可读取的 Caltech 正文，不根据搜索摘要补造 Cornell 节点。Johns Hopkins Trustees 页面访问不稳定，相关治理细节保持未知。Meta 公司介绍页要求登录，改用可读取的 IR 页面及 SEC 2026-04-08 8-K 核验职位与所在地。没有绕过访问限制。

待补：多数组织最新人数和逐项审计财务、未知领导人、各校具体内设机构、股权投票权、章程表决门槛、法律实体层次更完整的中间控股链、各组织最新新闻的持续维护。已有发布入口不等于实时新闻抓取。

## 示例路径与官方证据

- [UC 系统](../data/entities/university/uc-system.md) → [UC Berkeley](../data/entities/university/uc-berkeley.md)：[官方十校区名单](https://www.universityofcalifornia.edu/about-uc/campuses-locations)。
- [UT System](../data/entities/university/ut-system.md) → [UT Austin](../data/entities/university/utexas-austin.md)：[系统院校目录](https://www.utsystem.edu/institutions)。
- [Federal Reserve System](../data/entities/finance/us-federal-reserve-system.md) → [FOMC](../data/entities/finance/us-fomc.md)：[体系组成说明](https://www.federalreserve.gov/aboutthefed/fedexplained/who-we-are.htm)。
- [Alphabet](../data/entities/enterprise/alphabet.md) → [Google LLC](../data/entities/enterprise/alphabet-google.md)：[SEC FY2025 子公司披露](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/googexhibit2101q42025.htm)。
- [Bank of America Corporation](../data/entities/finance/bofa-corp.md) → [Bank of America, N.A.](../data/entities/finance/bofa-na.md)：[官网法律实体说明](https://investor.bankofamerica.com/shareholder-information/shareholder-and-contact-info)。

## 组织与来源索引

以下列出各记录的官网与本轮关键来源，完整来源列表在对应 Markdown YAML。只依据已读取正文写事实；索引和发布日期仍须逐条复核才能升级为完整核验。

|组织|官网|关键来源|
|---|---|---|
|[布朗大学](../data/entities/university/brown.md)|[官网](https://www.brown.edu/)|[来源](https://www.brown.edu/about/finances)|
|[加州理工学院](../data/entities/university/caltech.md)|[官网](https://www.caltech.edu/)|[来源](https://board.caltech.edu/)|
|[芝加哥大学](../data/entities/university/chicago.md)|[官网](https://www.uchicago.edu/)|[来源](https://www.uchicago.edu/who-we-are/leadership)|
|[哥伦比亚大学](../data/entities/university/columbia.md)|[官网](https://www.columbia.edu/)|[来源](https://secretary.columbia.edu/directory)|
|[达特茅斯学院](../data/entities/university/dartmouth.md)|[官网](https://home.dartmouth.edu/)|[来源](https://trustees.dartmouth.edu/)|
|[杜克大学](../data/entities/university/duke.md)|[官网](https://www.duke.edu/)|[来源](https://trustees.duke.edu/)|
|[佛罗里达大学](../data/entities/university/florida.md)|[官网](https://www.ufl.edu/)|[来源](https://trustees.ufl.edu/)|
|[佐治亚理工学院](../data/entities/university/georgia-tech.md)|[官网](https://www.gatech.edu/)|[来源](https://www.usg.edu/regents/)|
|[哈佛大学](../data/entities/university/harvard.md)|[官网](https://www.harvard.edu/)|[来源](https://www.harvard.edu/about/leadership-and-governance/)|
|[约翰斯·霍普金斯大学](../data/entities/university/johns-hopkins.md)|[官网](https://www.jhu.edu/)|[来源](https://www.jhu.edu/about/history/)|
|[密歇根大学](../data/entities/university/michigan.md)|[官网](https://umich.edu/)|[来源](https://regents.umich.edu/regents//)|
|[麻省理工学院](../data/entities/university/mit.md)|[官网](https://www.mit.edu/)|[来源](https://facts.mit.edu/leadership/)|
|[西北大学](../data/entities/university/northwestern.md)|[官网](https://www.northwestern.edu/)|[来源](https://www.northwestern.edu/about/board-of-trustees/)|
|[俄亥俄州立大学](../data/entities/university/ohio-state.md)|[官网](https://www.osu.edu/)|[来源](https://trustees.osu.edu/)|
|[普林斯顿大学](../data/entities/university/princeton.md)|[官网](https://www.princeton.edu/)|[来源](https://www.princeton.edu/meet-princeton)|
|[斯坦福大学](../data/entities/university/stanford.md)|[官网](https://www.stanford.edu/)|[来源](https://www.stanford.edu/about/leadership-and-governance/)|
|[加州大学伯克利分校](../data/entities/university/uc-berkeley.md)|[官网](https://www.berkeley.edu/)|[来源](https://www.universityofcalifornia.edu/about-uc/leadership)|
|[加州大学戴维斯分校](../data/entities/university/uc-davis.md)|[官网](https://www.ucdavis.edu/)|[来源](https://www.universityofcalifornia.edu/about-uc/leadership)|
|[加州大学欧文分校](../data/entities/university/uc-irvine.md)|[官网](https://uci.edu/)|[来源](https://www.universityofcalifornia.edu/about-uc/leadership)|
|[加州大学默塞德分校](../data/entities/university/uc-merced.md)|[官网](https://www.ucmerced.edu/)|[来源](https://www.universityofcalifornia.edu/about-uc/leadership)|
|[加州大学河滨分校](../data/entities/university/uc-riverside.md)|[官网](https://www.ucr.edu/)|[来源](https://www.universityofcalifornia.edu/about-uc/leadership)|
|[加州大学圣地亚哥分校](../data/entities/university/uc-sandiego.md)|[官网](https://ucsd.edu/)|[来源](https://www.universityofcalifornia.edu/about-uc/leadership)|
|[加州大学旧金山分校](../data/entities/university/uc-sanfrancisco.md)|[官网](https://www.ucsf.edu/)|[来源](https://www.universityofcalifornia.edu/about-uc/leadership)|
|[加州大学圣巴巴拉分校](../data/entities/university/uc-santabarbara.md)|[官网](https://www.ucsb.edu/)|[来源](https://www.universityofcalifornia.edu/about-uc/leadership)|
|[加州大学圣克鲁兹分校](../data/entities/university/uc-santacruz.md)|[官网](https://www.ucsc.edu/)|[来源](https://www.universityofcalifornia.edu/about-uc/leadership)|
|[加利福尼亚大学系统](../data/entities/university/uc-system.md)|[官网](https://www.universityofcalifornia.edu/)|[来源](https://www.universityofcalifornia.edu/about-uc/leadership)|
|[加州大学洛杉矶分校](../data/entities/university/uc-ucla.md)|[官网](https://www.ucla.edu/)|[来源](https://www.universityofcalifornia.edu/about-uc/leadership)|
|[宾夕法尼亚大学](../data/entities/university/upenn.md)|[官网](https://www.upenn.edu/)|[来源](https://www.upenn.edu/about/trustees-and-administration)|
|[佐治亚州大学系统](../data/entities/university/usg-system.md)|[官网](https://www.usg.edu/)|[来源](https://www.usg.edu/regents/)|
|[得克萨斯大学系统](../data/entities/university/ut-system.md)|[官网](https://www.utsystem.edu/)|[来源](https://www.utsystem.edu/institutions)|
|[得克萨斯大学奥斯汀分校](../data/entities/university/utexas-austin.md)|[官网](https://www.utexas.edu/)|[来源](https://www.utsystem.edu/institutions)|
|[华盛顿大学](../data/entities/university/washington.md)|[官网](https://www.washington.edu/)|[来源](https://www.washington.edu/regents/)|
|[耶鲁大学](../data/entities/university/yale.md)|[官网](https://www.yale.edu/)|[来源](https://www.yale.edu/about-yale/leadership-organization)|
|[Alphabet Capital US LLC](../data/entities/enterprise/alphabet-capital.md)|[官网](https://abc.xyz/)|[来源](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/googexhibit2101q42025.htm)|
|[Google 有限责任公司](../data/entities/enterprise/alphabet-google.md)|[官网](https://about.google/)|[来源](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/googexhibit2101q42025.htm)|
|[XXVI 控股公司](../data/entities/enterprise/alphabet-xxvi.md)|[官网](https://abc.xyz/)|[来源](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/googexhibit2101q42025.htm)|
|[Alphabet 公司](../data/entities/enterprise/alphabet.md)|[官网](https://abc.xyz/)|[来源](https://abc.xyz/investor/board-and-governance/default.aspx)|
|[亚马逊公司](../data/entities/enterprise/amazon.md)|[官网](https://www.aboutamazon.com/)|[来源](https://ir.aboutamazon.com/annual-reports-proxies-and-shareholder-letters/default.aspx)|
|[苹果公司](../data/entities/enterprise/apple.md)|[官网](https://www.apple.com/)|[来源](https://www.apple.com/leadership/)|
|[伯克希尔·哈撒韦](../data/entities/enterprise/berkshire-hathaway.md)|[官网](https://www.berkshirehathaway.com/)|[来源](https://www.berkshirehathaway.com/govern/govern.html)|
|[波音公司](../data/entities/enterprise/boeing.md)|[官网](https://www.boeing.com/)|[来源](https://boeing.mediaroom.com/2022-05-05-Boeing-Names-Northern-Virginia-Office-Its-Global-Headquarters-Establishes-Research-Technology-Hub)|
|[礼来公司](../data/entities/enterprise/eli-lilly.md)|[官网](https://www.lilly.com/)|[来源](https://www.lilly.com/about/contact)|
|[埃克森美孚](../data/entities/enterprise/exxonmobil.md)|[官网](https://corporate.exxonmobil.com/)|[来源](https://corporate.exxonmobil.com/who-we-are/contact-us/directory)|
|[强生公司](../data/entities/enterprise/johnson-johnson.md)|[官网](https://www.jnj.com/)|[来源](https://www.jnj.com/corporate-governance/articles-of-incorporation)|
|[Meta 平台公司](../data/entities/enterprise/meta.md)|[官网](https://about.meta.com/)|[来源](https://investor.atmeta.com/leadership-and-governance/)|
|[微软公司](../data/entities/enterprise/microsoft.md)|[官网](https://www.microsoft.com/)|[来源](https://www.microsoft.com/investor/reports/ar25/index.html)|
|[英伟达公司](../data/entities/enterprise/nvidia.md)|[官网](https://www.nvidia.com/)|[来源](https://investor.nvidia.com/financial-info/annual-reports-and-proxies/default.aspx)|
|[特斯拉公司](../data/entities/enterprise/tesla.md)|[官网](https://www.tesla.com/)|[来源](https://www.tesla.com/contact)|
|[沃尔玛公司](../data/entities/enterprise/walmart.md)|[官网](https://corporate.walmart.com/)|[来源](https://corporate.walmart.com/about)|
|[贝莱德](../data/entities/finance/blackrock.md)|[官网](https://www.blackrock.com/corporate/)|[来源](https://www.blackrock.com/corporate/about-us/who-we-are/contacts-and-locations)|
|[美国银行公司](../data/entities/finance/bofa-corp.md)|[官网](https://investor.bankofamerica.com/)|[来源](https://investor.bankofamerica.com/corporate-governance)|
|[美国银行全国协会](../data/entities/finance/bofa-na.md)|[官网](https://www.bankofamerica.com/)|[来源](https://investor.bankofamerica.com/regulatory-and-other-filings/subsidiary-and-country-disclosures?force_isolation=true)|
|[花旗集团](../data/entities/finance/citigroup.md)|[官网](https://www.citigroup.com/)|[来源](https://www.citigroup.com/global/about-us/leadership)|
|[高盛集团](../data/entities/finance/goldman-sachs.md)|[官网](https://www.goldmansachs.com/)|[来源](https://www.goldmansachs.com/what-we-do/our-businesses)|
|[摩根大通](../data/entities/finance/jpmorgan-chase.md)|[官网](https://www.jpmorganchase.com/)|[来源](https://www.jpmorganchase.com/about/governance)|
|[摩根士丹利](../data/entities/finance/morgan-stanley.md)|[官网](https://www.morganstanley.com/)|[来源](https://www.morganstanley.com/about-us-governance)|
|[美国联邦储备委员会](../data/entities/finance/us-fed.md)|[官网](https://www.federalreserve.gov/)|[来源](https://www.federalreserve.gov/aboutthefed/bios/board/default.htm)|
|[美国联邦储备系统](../data/entities/finance/us-federal-reserve-system.md)|[官网](https://www.federalreserve.gov/)|[来源](https://www.federalreserve.gov/aboutthefed/fedexplained/who-we-are.htm)|
|[联邦公开市场委员会](../data/entities/finance/us-fomc.md)|[官网](https://www.federalreserve.gov/monetarypolicy/fomc.htm)|[来源](https://www.federalreserve.gov/monetarypolicy/fomc.htm)|
|[纽约联邦储备银行](../data/entities/finance/us-nyfed.md)|[官网](https://www.newyorkfed.org/)|[来源](https://www.newyorkfed.org/aboutthefed/governance)|
|[富国银行集团](../data/entities/finance/wells-fargo.md)|[官网](https://www.wellsfargo.com/)|[来源](https://www.wellsfargo.com/biz/help/addresses/)|

本轮及继承记录引用的官方域名共 72 个（含同一机构不同子域）：

`abc.xyz`, `about.bankofamerica.com`, `about.google`, `accountability.universityofcalifornia.edu`, `board.caltech.edu`, `boeing.mediaroom.com`, `corporate.exxonmobil.com`, `corporate.walmart.com`, `facts.mit.edu`, `finance.harvard.edu`, `home.dartmouth.edu`, `investor.atmeta.com`, `investor.bankofamerica.com`, `investor.nvidia.com`, `ir.aboutamazon.com`, `newsroom.bankofamerica.com`, `regents.umich.edu`, `secretary.columbia.edu`, `trustees.dartmouth.edu`, `trustees.duke.edu`, `trustees.osu.edu`, `trustees.ufl.edu`, `uci.edu`, `ucsd.edu`, `www.aboutamazon.com`, `www.amazon.jobs`, `www.apple.com`, `www.berkeley.edu`, `www.berkshirehathaway.com`, `www.blackrock.com`, `www.boeing.com`, `www.brown.edu`, `www.citigroup.com`, `www.columbia.edu`, `www.duke.edu`, `www.federalreserve.gov`, `www.gatech.edu`, `www.goldmansachs.com`, `www.harvard.edu`, `www.jhu.edu`, `www.jnj.com`, `www.jpmorganchase.com`, `www.lilly.com`, `www.microsoft.com`, `www.mit.edu`, `www.morganstanley.com`, `www.newyorkfed.org`, `www.northwestern.edu`, `www.nvidia.com`, `www.osu.edu`, `www.princeton.edu`, `www.sec.gov`, `www.stanford.edu`, `www.tesla.com`, `www.ucdavis.edu`, `www.uchicago.edu`, `www.ucla.edu`, `www.ucmerced.edu`, `www.ucop.edu`, `www.ucr.edu`, `www.ucsb.edu`, `www.ucsc.edu`, `www.ucsd.edu`, `www.ucsf.edu`, `www.universityofcalifornia.edu`, `www.upenn.edu`, `www.usg.edu`, `www.utexas.edu`, `www.utsystem.edu`, `www.washington.edu`, `www.wellsfargo.com`, `www.yale.edu`。
