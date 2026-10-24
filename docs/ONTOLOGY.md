# 本体定义：节点与强依赖边

## 0. 研究视角：国家是“范围”，不是虚假的大股东

`jurisdiction=US` 表示实体主要所处法域，**不是**真实的 `PART_OF` 边。主页“美国”是导航容器，不参与强依赖图。将以下多个不连通组织子图分别展示：

- 美国联邦政府：行政、立法、司法三大分支；
- 各州、州属部门与地方政府：未来按州法/当地宪制单独建模，**不能默认美国总统 -> 州长 -> 市长**；
- 大学系统：按实际章程与治理结构建模；
- 企业集团：以正式股权/合并报表/法定控制为证据；
- 金融机构：按法人控股关系，而非“所有金融企业都归财政部管理”。

行政部门属于联邦行政分支，但并不意味着其全部行政决定都被总统个人直接实施。**“组成某系统” ≠ “对某自然人负责”**。

## 1. Entity Node

`id`: 稳定唯一字符串，不使用名称直接当 ID。

`category`：

- `government_system`、`government_branch`、`legislative_body`、`court`
- `executive_department`、`executive_agency`、`independent_agency`
- `university_system`、`university_campus`
- `enterprise_group`、`company_subsidiary`
- `financial_group`、`regulated_bank`

扩展时新增 `government_unit`、`nonprofit`、`public_corporation`、`research_institute` 等，并更新前端标签；不要强行把所有节点叫“法人”，因为国家政府分支/内设部门未必是独立法人。

`role` / `appointment`: 人物与组织不混为一个节点：个人是未来的另一种实体；最小版将公开任职信息作为嵌套属性，其岗位、任职状态和证据必须可查。

## 2. Strong edge relation

**存储方向：子/受依赖节点 -> 上级/资源提供者节点。**

| type | 条件 | 反例 |
|---|---|---|
| `PART_OF` | 法定或正式组织组成，A 是 B 内设单位/校区/部件 | A 从 B 获得一笔资助 |
| `REPORTS_TO` | 组织或机构依法定职责向 B 汇报/负责，须给出明确条款 | 官员任命、媒体口头描述 |
| `CONTROLLED_BY` | B 对 A 拥有正式控制权（股权、治理或合法控制） | B 对 A 存在一般行业监管 |
| `FUNCTION_DELEGATED_BY` | B 正式将特定功能委托 A 执行，标注委托对象/授权范围 | 仅与 B 同属于同一行业 |
| `FINANCIALLY_DEPENDENT_ON` | B 对 A 形成持续、可量化的运营资金依赖 | 单一采购、单一奖助、未核验的主要客户 |

资金依赖工程标准（**不是法律标准**）：在可比的两个连续年度内，B 资金贡献均超过 A 运营资金来源 50%；明确统计口径、分子、分母、年份、币种和证据。后续针对政府/非营利/公司可以制定不同标准。不得将“获批合同总金额”当作实际付款。

一对节点可以有多种真实关系，但每一种都须独立证据。不要把 `CONTROLLED_BY` 的证据复制粘贴来声称 `REPORTS_TO`。

## 3. 独立于结构层的关系与金融机制

- `REGULATES`：监管，非组织从属；未来在可选覆盖层展示。
- `FUNDS` / `GRANT_AWARDED_TO`：资助，不自动等于强依赖；作为资金事件单独建模。
- `CONTRACTED_WITH`：采购合同，不代表组织从属。
- `COLLABORATES_WITH`、`COMPETES_WITH`：合作和竞争；第一阶段不收录到依赖主图。

v0.2 已实现 `data/flows/` 金融机制层：税收、预算授权、国债融资、存款、信贷、利率、公开市场操作、股权融资、分红及科研资金等。`basis: mechanism` 描述制度如何工作，不证明每笔交易发生；`amount: null`。家庭、企业部门、投资者、银行体系、大学部门、资本市场、联邦预算为概念部门，与组织实体区分。财政授权和货币决策指令也不是现金转账。

事件层保存关联机构，新闻共同出现不生成结构边。资金流方向从来源到去向，不能与结构记录的子到父方向混淆。

## 4. 财务事实的不等价字段

`authorized_budget` 预算授权；`appropriation` 拨款；`obligation` 承诺支出；`outlay` 实际支出；`contract_value` 合同金额；`recognized_revenue` 会计确认收入；`net_income` 净利润；`cash_flow` 现金流。

不同组织的财务报表口径不同，禁止默认两种金额等价。建议财务指标记录 `type, value, currency, reporting_period, reporting_scope, source_url, reviewed_at`。

## 5. 时间化事实

每项关系最终需包含：`valid_from`/`valid_to`（现实有效期），`observed_at`（系统观测日期），`source_published_at`（公告日期），`evidence_url`。三者不能互相代替。

## 6. UI 反向画线说明

语义上 `A PART_OF B` 是 A -> B；在自上而下的目录视图中则显示 B 在上、A 在下，用“包含 A”的反向**导航箭头**。导航方向不是法律关系方向。右侧详情保留真实语义和证据。

## 7. 治理与地理

`governance.apex` 为最高治理主体或法定决策岗位，`mechanism` 为决定形成的制度过程。单一负责人字段不替代集体治理主体。`funding_model` 是带来源的定性资金模式，不是资产负债表。`location.precision` 区分城市近似位置、校区与总部；研究档案含城市近似位置，IPEDS 名录采用来源报告的校园坐标。联邦体系等制度容器可没有唯一地理位置，禁止任意用下属或首都替代。
