"""Daily/minute bars, indices, sectors, disclosures; no third-party dependency."""
import argparse
import datetime as dt
import re
from core import TZ, SOURCE, now, num, sid, trading_day, phase, request_json, data_of, emit
from quotes import query

HISTORY = 'https://push2his.eastmoney.com'


def parse_bars(data, code, period, received=None):
    received = received or now()
    if data.get('code') != sid(code).split('.')[1] or not data.get('name'):
        raise ValueError('K线证券身份不匹配')
    rows = data.get('klines')
    if not isinstance(rows,list) or not rows:
        raise ValueError('没有K线，不以空数组冒充成功')
    bars, previous = [], None
    for line in rows:
        parts = line.split(',')
        if len(parts) < 7:
            raise ValueError('K线字段不完整')
        label = parts[0]
        moment = dt.datetime.fromisoformat(label).replace(tzinfo=TZ)
        if moment.date() > received.date() or (period != 'day' and moment > received):
            raise ValueError('K线含未来记录或时钟偏差')
        if previous is not None and moment <= previous:
            raise ValueError('K线重复或非升序')
        previous = moment
        o,c,h,l,v,a = [num(float(x)) for x in parts[1:7]]
        missing_open = period == '1' and o == 0
        if min(c,h,l) <= 0 or (not missing_open and o <= 0) or l > c or h < c or (not missing_open and (l > o or h < o)) or v < 0 or a < 0:
            raise ValueError('K线OHLCV不合法')
        if period == 'day':
            # Same-day daily bar stays provisional even after 15:00.
            completed = moment.date() < received.date() and trading_day(moment.date()) is True
        else:
            # Upstream bar-label convention is not trusted; wait one full interval.
            completed = moment + dt.timedelta(minutes=int(period)) < received and trading_day(moment.date()) is True
        bars.append({'time':label,'open':None if missing_open else o,'close':c,'high':h,'low':l,
                     'missing_fields':['open'] if missing_open else [],
                     'volume_lots':v,'volume_shares':v*100,'turnover_cny':a,
                     'completed':completed})
    return bars


def bars(code, period='day', adjust='none', cache_dir=None, start=None, end=None):
    if period not in ('day','1','5','15') or adjust not in ('none','qfq','hfq'):
        raise ValueError('仅支持day/1/5/15及none/qfq/hfq')
    if period == '1' and adjust != 'none':
        raise ValueError('1分钟数据只支持未复权，不静默忽略复权参数')
    start = start or (now().date()-dt.timedelta(days=450)).strftime('%Y%m%d')
    end = end or now().strftime('%Y%m%d')
    for value in (start,end):
        dt.datetime.strptime(value,'%Y%m%d')
    if start > end:
        raise ValueError('开始日期晚于结束日期')
    if period == '1':
        path = '/api/qt/stock/trends2/get'
        params = {'secid':sid(code),'fields1':'f1,f2,f3,f4,f5,f6,f7,f8',
                  'fields2':'f51,f52,f53,f54,f55,f56,f57,f58','ndays':5,'iscr':0}
        def convert(raw):
            d = raw['data']
            return {**d,'klines':d.get('trends')}
    else:
        path = '/api/qt/stock/kline/get'
        params = {'secid':sid(code),'klt':101 if period=='day' else int(period),
                  'fqt':{'none':0,'qfq':1,'hfq':2}[adjust],'beg':start,'end':end,
                  'fields1':'f1,f2,f3,f4,f5,f6',
                  'fields2':'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61'}
        def convert(raw):
            return raw['data']
    def validate(raw):
        parse_bars(convert(raw),code,period)
    e = request_json(HISTORY+path,params,cache_dir=cache_dir,
                     cache_key='bars-v1',validate=validate)
    parsed = parse_bars(convert(e['payload']),code,period)
    parsed = [b for b in parsed if start <= b['time'][:10].replace('-','') <= end]
    if not parsed:
        raise ValueError('指定日期窗没有数据，分钟历史范围可能受上游限制')
    finished = [b for b in parsed if b['completed']]
    ma = {}
    if period == 'day':
        for n in (5,10,20):
            ma[str(n)] = round(sum(b['close'] for b in finished[-n:])/n,4) if len(finished)>=n else None
    return {'code':sid(code),'period':period,'adjust':adjust,'source':SOURCE,
            'query_time':now().isoformat(),'request_sent_at':e['request_sent_at'],
            'response_received_at':e['response_received_at'],'cache_status':e['cache_status'],
            'cached_at':e.get('cached_at'),'refresh_errors':e.get('refresh_errors',[]),
            'available_start':parsed[0]['time'],'available_end':parsed[-1]['time'],
            'completed_count':len(finished),'ma_completed_days':ma,
            'execution_prices':adjust=='none','bars':parsed,
            'limitations':['1分钟最多近5个交易日；其他频率实际覆盖以返回为准',
                            '分钟柱按标签后一个完整周期保守确认；今日日K始终视为未完成',
                            '复权数据不可直接作为委托价格；缓存仅供研究，不能触发入场']}


def sectors(kind='industry', board=None):
    if kind not in ('industry','concept'):
        raise ValueError('板块分类只能为industry/concept')
    if board and not re.fullmatch(r'BK\d{4}',board):
        raise ValueError('请先查询返回的真实BK板块代码')
    fs = 'b:'+board if board else 'm:90+t:' + ('2' if kind=='industry' else '3')
    e = request_json('https://push2.eastmoney.com/api/qt/clist/get',{
        'pn':1,'pz':200,'po':1,'np':1,'fltt':2,'invt':2,'fid':'f3','fs':fs,
        'fields':'f2,f3,f6,f12,f13,f14,f124'})
    d = data_of(e)
    rows = d.get('diff',[])
    rows = list(rows.values()) if isinstance(rows,dict) else rows
    if not isinstance(rows,list) or not rows:
        raise ValueError('没有板块数据')
    return {'kind':kind,'board':board,'source':SOURCE,'query_time':now().isoformat(),
            'returned':len(rows),'total':d.get('total'),'complete':len(rows)==d.get('total'),
            'rows':rows,'limitations':['仅返回前200条；不完整时不得计算全市场广度',
                                       '缺f124时不能将请求时间当作板块实际行情时间',
                                       '板块成分反映当前快照，不可直接用于无未来信息的历史回测']}


def announcements(code, start, end, max_pages=3):
    c = sid(code).split('.')[1]
    dt.date.fromisoformat(start)
    dt.date.fromisoformat(end)
    if start > end or not 1 <= max_pages <= 5:
        raise ValueError('公告查询范围或页数不合法')
    base = 'https://www.cninfo.com.cn'
    lookup = request_json(base+'/new/information/topSearch/query',form={'keyWord':c,'maxNum':10})['payload']
    if not isinstance(lookup,list):
        raise ValueError('巨潮证券检索格式变动，停止而不是猜orgId')
    matches = [x for x in lookup if str(x.get('code'))==c and x.get('orgId')]
    if len(matches)!=1:
        raise ValueError('巨潮证券身份无法唯一确认')
    org = matches[0]['orgId']
    output, seen, more = [], set(), False
    for page in range(1,max_pages+1):
        e = request_json(base+'/new/hisAnnouncement/query',form={
            'stock':c+','+org,'tabName':'fulltext','column':'szse' if sid(code).startswith('0.') else 'sse',
            'pageSize':30,'pageNum':page,'seDate':start+'~'+end,'isHLtitle':'false'})
        raw = e['payload']
        if 'announcements' not in raw:
            raise ValueError('公告响应缺关键字段')
        for row in raw.get('announcements') or []:
            if str(row.get('secCode'))!=c:
                continue
            key = row.get('announcementId')
            if key in seen:
                continue
            seen.add(key)
            title = re.sub('<[^>]+>','',row.get('announcementTitle',''))
            relative = row.get('adjunctUrl','')
            if not title or not relative.startswith('finalpage/') or '..' in relative:
                continue
            stamp = row.get('announcementTime')
            published = dt.datetime.fromtimestamp(num(stamp)/1000,TZ) if stamp else None
            if published and published > now():
                continue
            output.append({'id':key,'code':c,'title':title,
                'published_at':published.isoformat() if published else None,
                'url':'https://static.cninfo.com.cn/'+relative,
                'risk_keyword_hit':bool(re.search('减持|解禁|停牌|问询|风险|业绩|权益分派',title))})
        more = bool(raw.get('hasMore'))
        if not more:
            break
    return {'code':c,'source':'巨潮资讯公开披露','query_time':now().isoformat(),
            'date_range':[start,end],'announcements':output,'truncated':more,
            'coverage':'查询窗口内已公开标题索引，非完整未来事件日历',
            'limitations':['关键词仅提示复核，必须阅读公告正文；无结果不等于没有风险',
                            '未来事件日期须从原文核查，不能用公告发布时间替代事件时间']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command',required=True)
    k = sub.add_parser('bars')
    k.add_argument('code')
    k.add_argument('--period',choices=['day','1','5','15'],default='day')
    k.add_argument('--adjust',choices=['none','qfq','hfq'],default='none')
    k.add_argument('--start'); k.add_argument('--end'); k.add_argument('--cache-dir')
    sub.add_parser('indices')
    s = sub.add_parser('sectors')
    s.add_argument('--kind',choices=['industry','concept'],default='industry')
    s.add_argument('--board')
    a = sub.add_parser('announcements')
    a.add_argument('code'); a.add_argument('--start',required=True); a.add_argument('--end',required=True)
    a.add_argument('--max-pages',type=int,default=3)
    args = p.parse_args()
    try:
        if args.command=='bars':
            result = bars(args.code,args.period,args.adjust,args.cache_dir,args.start,args.end)
        elif args.command=='indices':
            result = query(['1.000001','0.399001','0.399006'])
        elif args.command=='sectors':
            result = sectors(args.kind,args.board)
        else:
            result = announcements(args.code,args.start,args.end,args.max_pages)
        emit({'ok':True,'result':result})
    except Exception as exc:
        emit({'ok':False,'error':str(exc),'query_time':now().isoformat()})
        raise SystemExit(1)


if __name__=='__main__':
    main()
