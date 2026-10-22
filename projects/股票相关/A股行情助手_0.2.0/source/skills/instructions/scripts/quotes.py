"""On-demand snapshots; positional CLI is backward compatible."""
import argparse
import concurrent.futures
import datetime as dt
from collections import Counter
from core import TZ, SOURCE, now, num, optional_num, sid, phase, request_json, data_of, load_json, emit

BASE = 'https://push2.eastmoney.com'
FIELDS = 'f58,f57,f43,f169,f170,f46,f44,f45,f47,f48,f60,f86,f168,f50'


def normalize(data, code, batch=False, received=None, envelope=None, record=None):
    received = received or now()
    if received.tzinfo is None:
        raise ValueError('查询时间必须含时区')
    received = received.astimezone(TZ)
    keys = ('f14','f12','f2','f3','f6','f124') if batch else ('f58','f57','f43','f170','f48','f86')
    name, actual, price, change, amount, stamp = [data.get(k) for k in keys]
    canonical = sid(code)
    if actual != canonical.split('.')[1] or not isinstance(name, str) or not name.strip():
        raise ValueError('返回股票名称/代码不匹配')
    price, change, amount, stamp = map(num, (price, change, amount, stamp))
    if price <= 0 or amount < 0 or stamp <= 0:
        raise ValueError('价格、成交额或来源时间不合法')
    source_time = dt.datetime.fromtimestamp(stamp, TZ)
    age = (received - source_time).total_seconds()
    if age < -60:
        raise ValueError('来源时间领先本机超过60秒，时间不可信')
    current_phase, source_phase = phase(received), phase(source_time)
    metadata_confirmed = False
    if record and record.get('status') == 'trading' and record.get('code') == actual:
        try:
            checked = dt.datetime.fromisoformat(record['checked_at'])
            metadata_confirmed = checked.tzinfo is not None and 0 <= (received - checked).total_seconds() <= 120
        except (ValueError, KeyError):
            pass
    if age < 0:
        quality, status = 'clock_skew', '盘中快照（时钟偏差，实时性未确认）'
    elif source_time.date() < received.date():
        quality, status = 'historical', '历史行情（非实时）'
    elif current_phase == 'continuous' and source_phase == 'continuous' and age <= 120:
        quality = 'realtime' if metadata_confirmed else 'fresh_unconfirmed'
        status = '实时行情（时间和个股状态已核验）' if metadata_confirmed else '盘中快照（时间新鲜，个股交易状态未确认）'
    elif current_phase == 'after_close' and source_time.time() >= dt.time(15):
        quality, status = 'close_unconfirmed', '收盘后快照（正式收盘更新状态未确认）'
    elif age > 120 and source_time.date() == received.date():
        quality, status = 'delayed', '延迟快照（非实时）'
    else:
        quality, status = 'session_unconfirmed', '当日快照（休市、午休或交易阶段待确认）'
    o, h, l, prev, volume = ('f17','f15','f16','f18','f5') if batch else ('f46','f44','f45','f60','f47')
    extras = {k: optional_num(data.get(v)) for k, v in
              [('open',o),('high',h),('low',l),('previous_close',prev),('volume_lots',volume)]}
    extras['volume_shares'] = extras['volume_lots'] * 100 if extras['volume_lots'] is not None else None
    if extras['volume_lots'] is not None and extras['volume_lots'] < 0:
        raise ValueError('成交量不能为负')
    missing = [k for k in ('open','high','low','previous_close','volume_lots') if extras[k] is None]
    if all(extras[k] is not None for k in ('open','high','low')):
        if extras['low'] <= 0 or extras['low'] > min(price, extras['open']) or extras['high'] < max(price, extras['open']):
            raise ValueError('开高低与最新价不一致')
    prev_price = extras['previous_close']
    if prev_price is not None:
        if prev_price <= 0 or abs((price / prev_price - 1) * 100 - change) > 0.03:
            raise ValueError('最新价、昨收和涨跌幅不一致')
    result = {'name':name,'code':actual,'secid':canonical,'latest_price':price,
              'change_pct':change,'change':round(price-prev_price,4) if prev_price else None,
              'turnover_cny':amount,**extras,
              'turnover_pct':optional_num(data.get('f8' if batch else 'f168')),
              'volume_ratio':optional_num(data.get('f10' if batch else 'f50')),
              'quote_time':source_time.isoformat(),'query_time':received.isoformat(),
              'age_seconds':round(age,3),'clock_skew':age < 0,
              'current_phase':current_phase,'source_phase':source_phase,
              'security_status_confirmed':metadata_confirmed,'quality':quality,
              'quote_status':status,'missing_fields':missing,'source':SOURCE,
              'units':{'price':'CNY','amount':'CNY','volume_lots':'手(100股)','volume_shares':'股'},
              'fltt':2,'cache_status':'network'}
    if envelope:
        result.update({k:envelope.get(k) for k in ('request_sent_at','response_received_at','server_date','attempts')})
    if canonical.startswith('1.000') or canonical.startswith('0.399'):
        result['volume_raw'] = result['volume_lots']
        result['volume_lots'] = result['volume_shares'] = None
        result['units'].update(volume_lots=None, volume_shares=None, volume_raw='上游指数口径，未换算')
    return result


def single(code, master=None):
    e = request_json(BASE+'/api/qt/stock/get', {'secid':sid(code),'fields':FIELDS,'fltt':2})
    return normalize(data_of(e),code,envelope=e,record=(master or {}).get(sid(code).split('.')[1]))


def query(codes, master=None):
    codes = list(dict.fromkeys(codes))
    results, errors, valid, batch_errors = {}, {}, [], []
    for code in codes:
        try:
            sid(code)
            valid.append(code)
        except ValueError as exc:
            errors[code] = str(exc)
    if len(valid) > 1:
        for offset in range(0,len(valid),50):
            chunk = valid[offset:offset+50]
            try:
                e = request_json(BASE+'/api/qt/ulist.np/get',{
                    'secids':','.join(sid(c) for c in chunk),'fltt':2,
                    'fields':'f2,f3,f5,f6,f8,f10,f12,f13,f14,f15,f16,f17,f18,f124'})
                rows = data_of(e).get('diff',[])
                rows = list(rows.values()) if isinstance(rows,dict) else rows
                for code in chunk:
                    matches = [r for r in rows if str(r.get('f12')) == sid(code).split('.')[1]
                               and str(r.get('f13')) == sid(code).split('.')[0]]
                    if len(matches) == 1:
                        try:
                            results[code] = normalize(matches[0],code,True,envelope=e,
                                record=(master or {}).get(sid(code).split('.')[1]))
                        except (ValueError,OverflowError,OSError) as exc:
                            batch_errors.append({'code':code,'reason':str(exc)})
            except Exception as exc:
                batch_errors.append({'codes':chunk,'reason':str(exc)})
    pending = [c for c in valid if c not in results or results[c]['quality'] in ('historical','delayed')
               or results[c]['missing_fields']]
    def fallback(code):
        try:
            return code,single(code,master),None
        except Exception as exc:
            return code,None,str(exc)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for code,q,error in pool.map(fallback,pending):
            if q:
                old = results.get(code)
                if not old or q['quote_time'] >= old['quote_time']:
                    results[code] = q
            elif code in results:
                results[code]['refresh_error'] = error
            else:
                errors[code] = error
    qualities = Counter(q['quality'] for q in results.values())
    return {'quotes':[results[c] for c in codes if c in results],
            'failures':[{'code':c,'reason':errors[c]} for c in codes if c in errors],
            'success_count':len(results),'failure_count':len(errors),
            'realtime_count':qualities['realtime'],'quality_counts':dict(qualities),
            'batch_errors':batch_errors,'retry_limit':2,
            'success_definition':'字段合格不等于实时；负年龄、休市或状态未知不计严格实时',
            'transport':'直接HTTPS；不是MCP工具调用','mcp_status':'not_verified'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('codes',nargs='+')
    p.add_argument('--master',help='经核验的证券主数据JSON，按六位代码索引')
    a = p.parse_args()
    emit(query([c.strip() for group in a.codes for c in group.split(',')],load_json(a.master) if a.master else None))

