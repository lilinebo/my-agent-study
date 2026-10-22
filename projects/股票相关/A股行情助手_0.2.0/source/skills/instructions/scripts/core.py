"""Shared on-demand data utilities; Python 3.9+, standard library only."""
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

TZ = dt.timezone(dt.timedelta(hours=8), 'Asia/Shanghai')
ROOT = Path(__file__).resolve().parent.parent
SOURCE = '东方财富公开接口'


def now():
    return dt.datetime.now(TZ)


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('数字缺失、非有限值或类型异常')
    return value


def optional_num(value):
    try:
        return num(value)
    except ValueError:
        return None


def sid(code):
    if re.fullmatch(r'[01]\.\d{6}', code):
        return code
    if re.fullmatch(r'(000|001|002|003|300|301|399)\d{3}', code):
        return '0.' + code
    if re.fullmatch(r'(600|601|603|605|688|689)\d{3}', code):
        return '1.' + code
    raise ValueError('证券标识无法确认；指数可使用明确的0./1.六位代码')


def calendar():
    return load_json(ROOT / 'references' / 'calendar-2026.json')


def trading_day(day, cal=None):
    cal = cal or calendar()
    if not (cal['valid_from'] <= day.isoformat() <= cal['valid_to']):
        return None
    if day.isoformat() in cal.get('open_overrides', []):
        return True
    closed = any(a <= day.isoformat() <= b for a, b in cal['closed_ranges'])
    return day.weekday() < 5 and not closed


def phase(moment, cal=None):
    if moment.tzinfo is None:
        raise ValueError('时间必须包含时区')
    moment = moment.astimezone(TZ)
    day = trading_day(moment.date(), cal)
    if day is None:
        return 'calendar_unknown'
    if not day:
        return 'closed_day'
    t = moment.time()
    if dt.time(9, 15) <= t < dt.time(9, 30):
        return 'opening_auction'
    if dt.time(9, 30) <= t < dt.time(11, 30) or dt.time(13) <= t < dt.time(14, 57):
        return 'continuous'
    if dt.time(11, 30) <= t < dt.time(13):
        return 'lunch'
    if dt.time(14, 57) <= t < dt.time(15):
        return 'closing_auction'
    return 'after_close' if t >= dt.time(15) else 'before_open'


def session_dates(first, count, cal=None):
    if trading_day(first, cal) is not True:
        raise ValueError('起始日不是已确认交易日，或交易日历尚未覆盖')
    result, day = [], first
    for _ in range(370):
        valid = trading_day(day, cal)
        if valid is None:
            raise ValueError('退出日期超出已核验交易日历；请更新日历')
        if valid:
            result.append(day.isoformat())
            if len(result) == count:
                return result
        day += dt.timedelta(days=1)
    raise ValueError('不能计算持有期')


def request_json(url, params=None, form=None, cache_dir=None, cache_key=None, validate=None):
    """Bounded retry. Only historical/research callers opt in to cache fallback."""
    if not url.startswith('https://'):
        raise ValueError('只允许HTTPS数据请求')
    if params:
        url += '?' + urllib.parse.urlencode(params)
    cache_path = None
    if cache_dir and cache_key:
        digest = hashlib.sha256((cache_key + url + str(form)).encode()).hexdigest()
        cache_path = Path(cache_dir) / (digest + '.json')
    errors = []
    for attempt in range(3):
        sent = now()
        try:
            body = urllib.parse.urlencode(form).encode() if form is not None else None
            headers = {'Accept': 'application/json', 'User-Agent': 'A-share-quotes/0.2.0'}
            if form is not None:
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers), timeout=10) as response:
                payload = json.load(response)
                server_date = response.headers.get('Date')
            received = now()
            if isinstance(payload, dict) and 'rc' in payload and (payload['rc'] != 0 or payload.get('data') is None):
                raise ValueError('接口错误或空data')
            if validate:
                validate(payload)
            envelope = {'payload':payload, 'request_sent_at':sent.isoformat(),
                        'response_received_at':received.isoformat(), 'server_date':server_date,
                        'attempts':attempt+1, 'cache_status':'network', 'cached_at':None, 'errors':errors}
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                temp = cache_path.with_suffix('.tmp')
                try:
                    temp.write_text(json.dumps(envelope, ensure_ascii=False, allow_nan=False), encoding='utf-8')
                    os.replace(temp, cache_path)
                except OSError as exc:
                    envelope['errors'].append('缓存写入失败: ' + str(exc))
            return envelope
        except urllib.error.HTTPError as exc:
            errors.append(str(exc))
            if exc.code != 429 and not 500 <= exc.code < 600:
                raise
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
        if attempt < 2:
            time.sleep(0.5 * 2 ** attempt)
    if cache_path and cache_path.exists():
        envelope = load_json(cache_path)
        envelope.update(cache_status='stale_fallback', cached_at=envelope['response_received_at'],
                        last_attempt_at=now().isoformat(), refresh_errors=errors)
        return envelope
    raise RuntimeError('有限重试后失败: ' + '; '.join(errors))


def data_of(envelope):
    return envelope['payload']['data']


def security_check(code, record=None):
    canonical = sid(code)
    c = canonical.split('.')[1]
    if not canonical.startswith('0.') or not re.fullmatch(r'(000|001|002|003)\d{3}', c):
        return {'eligible':False, 'reason':'不在已确认深市主板A股范围（创业板禁止）'}
    if not record or record.get('code') != c:
        return {'eligible':False, 'reason':'缺证券主数据，不能仅凭代码前缀放行'}
    if (record.get('exchange'), record.get('board'), record.get('kind')) != ('SZSE','MAIN','A_SHARE'):
        return {'eligible':False, 'reason':'主数据不符合深市主板A股资格'}
    if not record.get('source_url', '').startswith('https://'):
        return {'eligible':False, 'reason':'主数据缺原始来源'}
    if not record.get('name') or re.search(r'ST|退', record['name'], re.I):
        return {'eligible':False, 'reason':'名称异常或ST/退市风险'}
    if record.get('status') != 'trading' or record.get('unrestricted') is not False:
        return {'eligible':False, 'reason':'停牌、无涨跌幅限制或状态未核实'}
    listed = dt.date.fromisoformat(record['listed_date'])
    if (now().date() - listed).days < 30:
        return {'eligible':False, 'reason':'上市时间不足30自然日，初始策略排除'}
    checked = dt.datetime.fromisoformat(record['checked_at'])
    if checked.tzinfo is None:
        return {'eligible':False, 'reason':'证券核验时间缺时区'}
    age = (now() - checked.astimezone(TZ)).total_seconds()
    if age < 0 or age > 86400 or checked.astimezone(TZ).date() != now().date():
        return {'eligible':False, 'reason':'证券状态须当日重新核验'}
    return {'eligible':True, 'reason':'当日主数据核验通过，仍需人工核对券商权限'}
