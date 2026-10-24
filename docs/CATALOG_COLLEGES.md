# 美国高等及职业教育机构目录

组织世界模型将人工研究档案和官方全量目录合并显示。教育目录使用 NCES IPEDS 的 **HD2025 / 2025–26 目录**，于 **2026-10-24** 下载。年度目录不表示逐校核验下载当天的运营状态。

## 范围与数量

| 项目 | 数量 |
| --- | ---: |
| 官方 CSV 原始条目 | 5,985 |
| 位于 50 州和 DC 的原始条目 | 5,845 |
| 默认收录的教学机构 | 5,706 |
| 其中学位授予机构 | 3,877 |
| 其中非学位教育机构 | 1,829 |
| 有来源校园坐标 | 5,630 |
| 有来源支持的 HTTPS 官网 | 3,801 |
| 与既有人工校园档案准确对应 | 30 |

导入无数量截断、排名门槛或名校名单。筛选表达式为：`STABBR ∈ 50 states + DC`、`ACT ∈ {A,N,R}`、`CYACTIVE=1`、`SECTOR ∈ 1..9`、`CLOSEDAT` 为空或 `-2`。原始文件完整保留，筛选后的每条记录保留 `UNITID`、原始分类与系统名称字段。

**“学位授予”包括副学士、学士、硕士及博士等，不能把 5,706 个条目都称为四年制大学。** 非学位类别包括技术、职业与美容等学校；可通过 `source_fields.deggrant` 和 `source_fields.sector` 明确筛选。IPEDS 覆盖其报告宇宙，不声称囊括每一个现实存在的美国教育组织、每个大学内部学院或每个物理教学点。

未进入默认教学目录的 279 条依次按互斥规则记账：140 条位于 50 州和 DC 以外，70 条源期内非开放状态，69 条行政单位或非教学分类。140 条包含 PR 131、GU 3、AS 1、MP 1、VI 1、FM 1、MH 1、PW 1；后三者是自由联系国，不能统称美国领地。这些条目保留在原始 CSV，metadata 记录地域分布，未被静默丢弃。

`CYACTIVE=1` 也可能包含本年度关闭但仍须报送上一年数据的 `ACT=M`，所以不能仅以 `CYACTIVE` 认定在运营。`ACT=G` 是由主校代报的子校区记录，不作为独立教学机构加入本轮默认目录。行政单位与大学系统另行研究，不把系统与某个校园自动合并。

## 证据、地图与官网

- [完整 HD2025 官方数据](https://nces.ed.gov/ipeds/complete-data-files/HD2025.zip)，[官方字典](https://nces.ed.gov/ipeds/complete-data-files/HD2025_Dict.zip)。原始解压文件为 `data/sources/ipeds/hd2025.csv`、`hd2025.xlsx`，下载压缩包与解压文件的 SHA-256 均见同目录 `manifest.json`。
- [官方分组方法](https://nces.ed.gov/ipeds/use-the-data/institutional-groupings-in-ipeds)解释 UNITID、层次、性质、学位与地理分组。方法网页与[公开使用政策](https://nces.ed.gov/about/public-access-research)已留存 HTML 和可读文本。
- 地图直接使用原始 `LATITUDE` / `LONGITUD`，不把未知位置补成首都、州中心或系统总部。76 条无有效坐标，保留在总览并明确不可定位。`precision: campus` 表示来源校园位置，不保证精确入口、实际财产边界或所有分校的位置。
- `official_url` 接受原字段明确为 HTTPS 的地址，或原 `WEBADDR` 未写协议且同一行其他官网链接明确给出**完全相同主机**的 HTTPS；后者把证据链接和归一化理由保存于 `source_fields`。不把 HTTP 强改成 HTTPS，不以另一个子域名推断支持。未能确定的 1,905 条官网保留原字符串且可点 NCES 官方机构档案。
- 每条 `registry_url` 以 NCES College Navigator 的 UNITID 跳转。目录链接是官方报告记录，不代表本次打开并核验过全部数千所学校的网站。
- 不导入目录里的历史校长姓名为当前负责人，不由公私性质、学校系统名称或资助资格推导治理、控制或金融依赖。

## 与人工档案衔接

导入器有 30 个显式 `UNITID + HD2025 完整名称` 对照，包括 10 个 UC 校园及 20 个既有学校档案；源名称变化会报错要求复核，未采用模糊匹配。三个大学系统 `uc-system`、`usg-system`、`ut-system` 不映射成校园。源身份 `ipeds-{UNITID}` 始终保留；`curated_id` 仅让构建器避免同一校园重复计数，并继续展示人工核验的治理、职责和关系。

## 复现与更新

```bash
python3 scripts/import_colleges.py
python3 scripts/import_colleges.py --check
python3 -m unittest discover -s tests -p test_import_colleges.py -v
```

默认读取本地完整 CSV，结果稳定且无网络依赖。需要重新下载同年版本时才显式执行 `python3 scripts/import_colleges.py --download --retrieved-at YYYY-MM-DD`；不能用旧下载日期标记新文件。升级到新年度需同时复核字典、状态筛选、30 条校园对照和数据口径，并更新说明。未设置自动更新。

目录页 `DataFiles.aspx` 的直接抓取遇到重定向循环，未绕过；实际 CSV、数据字典及方法/许可页面均经官方公开地址成功下载。原始目录证据独立于该动态列表页。
