# 美国上市发行人名录

本轮以完整的官方证券目录替代手选企业：读取 Nasdaq Trader 的 [Nasdaq 上市证券](https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt) 和 [其他美国交易所上市证券](https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt)。字段含义依据 [Nasdaq Symbol Directory Definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs)，源文件自带创建时间。下载日为 2026-10-24，两个文件的原文创建时间均为 2026-10-23 21:31；源未给时区，未转换为 UTC。

SEC 的 [交易代码目录](https://www.sec.gov/files/company_tickers_exchange.json) 可通过网页检索阅读，但本地直接下载返回 HTTP 403。本次没有绕过访问限制，也没有把其他来源冒充 SEC。生成文件为 `data/catalogs/nasdaq.json`，`catalog_source` 为 `nasdaq`；原始文件保存在最初规划的 `data/sources/sec/` 目录，目录名不代表来源。

## 口径与数量

| 口径 | 数量 |
| --- | ---: |
| Nasdaq 原始证券行 | 5,625 |
| 其他交易所原始证券行 | 7,674 |
| 原始证券行合计 | 13,299 |
| 收录发行人名称组 | 5,913 |
| 归入名称组的证券行 | 7,321 |
| 合并的额外证券行 | 1,408 |
| 排除测试记录 | 37 |
| 排除非测试 ETF | 5,781 |
| 无法准确归入主证券发行人的辅助证券 | 160 |
| 与既有详细档案准确匹配 | 19 |

测试标记优先于 ETF 标记，因此同时命中二者的两行只计一次。全量排除清单为 `data/sources/sec/nasdaq_exclusions.json`。原始行数 = 收录证券行数 + 排除行数；证券行数与组织名称组数不能混用。

这里的“美国上市”描述交易市场，不描述注册地。包括外国发行人、SPAC、封闭式基金及其他非 ETF 主体，**不能称为美国本土经营公司全集**。没有截取前 100 家或市值门槛，也没有把 ETF 的管理公司名称当成 ETF 的法人身份。OTC 不在这两份目录范围内，交易所覆盖以原文件为准。

## 去重、匹配与未知

- Nasdaq 的明确发行人/证券描述分隔符，以及其他目录的明确普通股、ADR、股份类别后缀用于提取名称。只归一化大小写和空白；没有做模糊企业合并。
- 同一明确名称的不同股份类别合为一组，优先股、权证、债券等只在准确匹配已有主证券发行人时附在 `listings` 内。没有主证券匹配的辅助证券保留于排除审计，避免每只证券生成一个组织。
- 组 ID 为规范化名称的 SHA-256 前 16 位，不冒充 CIK/LEI。目录名称可能存在不同写法、发行主体变更或少量残留证券描述；5,913 是**发行人名称组数**，不是经过完整法人消歧的数量。
- `curated_id` 同时核对交易代码和源名称。Bank of America Corporation 对应 `bofa-corp`，不对应银行子公司 `bofa-na`；BlackRock 基金不合并到管理公司。
- XOM 源名称为 **ExxonMobil Holdings Corporation**，既有档案为 **Exxon Mobil Corporation**。没有因为品牌或代码相近而自动合并，须在后续核验重组、法律实体和生效日。
- 目录不提供已核验总部、公司官网、负责人、治理、公司控制关系或逐笔金融流。对应字段留空，`registry_url` 链接官方名录，不能在界面标成公司官网；也没有从公司名推断金融行业分类。

## 可复现更新

从已保存的快照离线生成：

```bash
.venv/bin/python scripts/import_companies.py --retrieved-at 2026-10-24
```

显式重新下载时使用 `--download` 并传实际下载日。普通构建不联网刷新。下载时检查表头和文件尾时间，生成器拒绝未知测试/ETF 标记；源字段或格式改变需先复核。每个原文件 SHA-256、创建时间、行数、链接均保存在 `metadata.raw_files`；`metadata.sha256` 对应 `raw_file`，另外提供组合清单哈希。

```bash
.venv/bin/python -m unittest discover -s tests -p test_import_companies.py -v
```

测试覆盖股份类别合并、ETF/测试排除、母子公司不误合并、基金与管理人区分、ADR/优先股语义、损坏输入拒绝、原始快照哈希和可复现生成。

Nasdaq 目录保持原始来源及权利声明；项目代码许可证不重新许可这些外部数据，未声明其具有开放数据许可证。没有采集报价或付费交易数据。
