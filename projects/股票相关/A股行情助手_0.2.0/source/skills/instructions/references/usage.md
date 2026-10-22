# 0.2.0按需运行说明

Python 3.9+，仅标准库，无需本地常驻服务。所有脚本位于同一scripts目录，调用时使用实际绝对路径；Windows可使用python -X utf8。旧quotes.py 六位代码入口保留。CLI返回JSON，research/trade_plan遇失败以ok=false和非零退出码结束；quotes逐股报告失败，必须检查failure_count，不能只看进程退出码。

## 命令

```text
python scripts/quotes.py 000731 000837 300750
python scripts/research.py indices
python scripts/research.py bars 000837 --period day --adjust none --cache-dir <授权工作目录>/cache
python scripts/research.py bars 000837 --period day --adjust qfq --start 20260101 --end 20261022
python scripts/research.py bars 000837 --period 1
python scripts/research.py bars 000837 --period 5
python scripts/research.py bars 000837 --period 15
python scripts/research.py sectors --kind industry
python scripts/research.py sectors --kind concept
python scripts/research.py sectors --board <上一步返回的BK代码>
python scripts/research.py announcements 000837 --start 2026-10-01 --end 2026-10-22
python scripts/trade_plan.py calculate 000837 --entry 10 --max-entry 10 --stop 9.80 --target 10.80 --buy-date 2026-10-22
python scripts/trade_plan.py record --journal <授权工作目录>/journal.jsonl --event <实际事件文件.json>
```

价格示例纯属计算演示，不是000837报价/建议。默认交易计算因主数据和费率未确认会列blockers，execution_ready永远为false，不生成可直接执行的指令。

## 当日证券主数据

可通过--master指定用户工作目录的JSON，结构为六位代码到记录的映射；以下字段仅为格式示意，不能照抄为已核验数据：

```json
{
  "000837": {
    "code": "000837", "name": "需核验的实际名称",
    "exchange": "SZSE", "board": "MAIN", "kind": "A_SHARE",
    "listed_date": "需核验YYYY-MM-DD", "status": "trading",
    "unrestricted": false,
    "checked_at": "实际核验时间，带+08:00",
    "source_url": "实际原始HTTPS来源"
  }
}
```

不要编造source_url/checked_at。证券主数据可查交易所/券商说明；动态停复牌、ST状态必须当日复查。quotes严格实时标签还要求近期状态记录（120秒内）；没有主数据不妨碍查询，但降级快照。主数据资格核验不能替代最新价格/事件审查。

## K线口径

- 日K/5/15分钟用东财历史接口；1分钟用trends2，只覆盖上游可返回的近5个交易日。
- volume_lots为手，volume_shares=手×100。指数成交数量不应按股票“股数”解释；指标研究应使用成交额或确认该指数数量口径。
- 日K仅前一日及之前且日历覆盖的记录标完成；当天即使盘后也不自动认定收盘确认。
- 分钟标签不同接口约定可能不同，当前采用“标签时间+周期小于查询时间”的保守完成方式；可能多等一根柱，不提前确认未完成K线。
- MA只用已完成日线。qfq/hfq不可直接用作委托价格，未实现自动因子映射。
- 历史请求有可选缓存；上游失败且命中旧缓存时cache_status=stale_fallback，必须标缓存日期。没有实时缓存回退。
- 包内2026交易日历依据深交所公告，超出年份必须更新；临时停市/个股停牌仍需当天核验。

## 板块与公告的能力边界

sectors提供行业/概念或指定板块当前前200行，返回total/complete；不是全市场扫描器，没有全市场涨跌停、炸板率或完整历史同刻量能。缺实际来源时间时不得做精确跨时刻排名。

announcements通过巨潮证券检索后查询原始PDF索引，最多5页；标truncated。公开网页接口可能变化、断开或受限，无结果不是无风险。仅标题风险词不能替代原文。未实现未来事件自动抽取、官方授权商业数据接入或全量监控。

## 实际成交记录

record显式追加用户指定文件，不联网。事件必须有唯一id、带时区time、type。买卖需plan_id、code、实际quantity、price、fees_cny；出入金需amount_cny。部分成交数量允许非整百（委托整手要求仍需单独核验）。以实际成交时间计算T+1和五日截止；只登记日志不接券商账户。

支持类型：plan、buy_fill、sell_fill、deposit、withdrawal、cancel、execution_error。首次成交前可先登记plan。重复id拒绝写入；记录不完整导致可卖量不足时拒绝登记卖出，先核对历史。日志不自动计算完整持仓净值或FIFO税务盈亏，复盘由助手根据完整流水核算。

## 版本与验证

0.2.0新增：时钟偏差降级、完整快照字段、上海指数与同代码深市股票消歧、2026日历、可选历史缓存、日K/1/5/15分钟、指数、板块列表与巨潮公告适配器、深市主板资格校验、含费滑点风险计算及本地成交日志。

原MCP连接、插件身份、默认提示与受众保留。没有恢复远端MCP，也不发布任何服务器。公开源不可用时按缺项降级。未来事件日历、独立备源、完整广度、自动信号监控与券商API不在本版实现范围。
