# 政府与公共机构官方目录

采集日为 **2026-10-24**。本层以官方完整索引提供广度，与人工研究档案的治理、隶属和金融解释合并。目录记录本身不代表已经核验了全部现行事实。

| 来源 | 原始记录 | 本地覆盖 |
| --- | ---: | --- |
| [Federal Register 全机构 API](https://www.federalregister.gov/api/v1/agencies.json) | 473 | 完整 API 响应，包含历史机构 |
| [USA.gov A–Z](https://www.usa.gov/agency-index) | 431 | 22 个字母分页中的全部机构卡片 |
| 跨来源同一身份合并 | 245 | 精确名称词项匹配或显式别名交叉表 |
| 集合、场所或明显非组织项目排除 | 9 | 原记录和排除理由列于 catalog metadata |
| 合并后的目录记录 | **650** | 其中 63 个身份链接既有研究档案 |

`473 + 431 − 245 − 9 = 650`。数量指本次两个来源之间完成身份归并的记录，不能作为全美国现存政府机构总数。国家制度容器、三分支和此前研究档案继续由人工事实层维护。

## 范围和证据边界

Federal Register 是发行文书的机构索引，保留 ACTION、历史委员会等记录；API `parent_id`、`child_ids` 和原说明仅存在 `source_fields` 中，**不会自动生成现行 `PART_OF` 或 `CONTROLLED_BY` 边**。其网站也注明网络呈现不是正式法律版本；本项目将它用于机构目录识别，不用接口说明取代法定文件。

USA.gov 的官方范围包括联邦机构、部门、政府公司、公共工具和政府支持企业。因此，“列于政府目录”不等于行政机关、政府所有或总统控制。USA.gov 上架状态也不构成独立核验的存续状态。所有目录级记录保留这项状态说明；不从官网可访问、目录存在或名称相似推断组织仍在运作。

未覆盖全部州、市、县、特别区、部落政府及全部法院、机构内部办公室。研究对象中的学校、GSE 等也可能同时进入高校或发行人目录；跨类型来源的进一步实体解析仍须以明确标识核对，不能为了降低数量而模糊合并。已知候选包括 Uniformed Services University、West Point、National Defense University、Fannie Mae 和 Freddie Mac。

官网仅接受来源实际提供的 HTTPS 地址。旧的 HTTP 地址保留在源字段；没有未经测试地将所有 HTTP 改成 HTTPS。没有官网的条目仍可通过 HTTPS 的官方名录页访问。无坐标、治理、员工、负责人或金额数据时保留未知。

## 可复现维护

```bash
# 使用已保存快照离线重建目录
.venv/bin/python scripts/import_agencies.py

# 明确联网刷新官方源并记录新的采集日；不是自动定时任务
.venv/bin/python scripts/import_agencies.py --download
```

源保存在 `data/sources/agencies/`，逐文件 SHA-256 与采集日在 `retrieval.json` 中。生成记录写入 `data/catalogs/agencies.json`。导入器验证源文件哈希、重复 ID、解析结构和交叉表一对一性；遇到官方页面变更会失败，不将空响应当作完成。

FR 与 USA.gov 的政府公开文本以来源快照形式留存，网页中的第三方图片或标记未被抽取到目录。技术依据为 [Federal Register API 文档](https://www.federalregister.gov/developers/documentation/api/v1)，该接口公开、不需 API 密钥。

## 十二家地区联储与金融流转

在已有纽约联储之外，新增波士顿、费城、克利夫兰、里士满、亚特兰大、芝加哥、圣路易斯、明尼阿波利斯、堪萨斯城、达拉斯和旧金山 **11 份研究档案、11 条体系组成关系及 11 个城市近似位置**。每份均附理事会对应银行页面的行长和地点证据。亚特兰大官网列 Cheryl Venable 为 interim president，数据保留 `interim`，没有写成正式任命。

十二家均属于 [美联储体系的地区运营机构](https://www.federalreserve.gov/aboutthefed/federal-reserve-system.htm)。九人董事会的组成来自 [理事会治理说明](https://www.federalreserve.gov/aboutthefed/directors/about.htm)；行长遴选由 B、C 类董事与理事会批准程序共同完成，依据 [行长遴选说明](https://www.federalreserve.gov/faqs/how-is-a-federal-reserve-bank-president-selected.htm)。这与会员股票的持有关系分开解释。

新增 17 条机制，使当前金融层达到 35 条：

- 12 家地区银行各自到银行部门的[贴现窗口机制](https://www.federalreserve.gov/monetarypolicy/discountrate.htm)，仅表示符合条件并提供抵押后的可用借款渠道，不说明具体银行已借款。
- [准备金余额利息](https://www.federalreserve.gov/monetarypolicy/reserve-balances.htm)，区分理事会设置利率与储备银行支付利息。
- [Fedwire 账户结算](https://www.federalreserve.gov/paymentsystems/fedfunds_about.htm)，区分服务操作入口与参加机构之间的实际账户划转。
- [国库账户与财政代理](https://www.federalreserve.gov/aboutthefed/fedexplained/who-we-are.htm)，不写成财政部向央行拨款。
- [法定会员资本与可分配净收益汇缴规则](https://www.federalreserve.gov/faqs/about_14986.htm)，不把特殊会员股票说成普通商业控制，不声称当前期间已经向财政部汇款。

所有机制均为 `basis: mechanism`、`amount: null`。箭头包含制度服务或资金运作方向，须阅读其说明；它不是逐笔交易账本，也不是央行直接向每一家企业放款的网络。

## 验证

`tests/test_import_agencies.py` 验证 HTML 实体解析、页面结构改变时失败、HTTPS 真实性、精确身份匹配、重复 ID 拒绝和完整快照计数守恒。全项目构建另外验证新增地区联储的结构、引用、位置、负责人状态及金融机制端点。
