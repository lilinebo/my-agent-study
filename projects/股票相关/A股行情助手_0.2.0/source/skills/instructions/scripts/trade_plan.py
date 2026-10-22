"""Risk calculator and explicit local journal; never submits brokerage orders."""
import argparse
import datetime as dt
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import uuid
from core import ROOT, TZ, now, load_json, emit, num, security_check, session_dates


def dec(v):
    if isinstance(v,bool):
        raise ValueError('金额不能为布尔值')
    value = Decimal(str(v))
    if not value.is_finite():
        raise ValueError('金额必须为有限值')
    return value


def money(v):
    return float(v.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))


def fee(buy, sell, profile):
    rate = dec(profile.get('commission_rate') or 0)
    minimum = dec(profile['minimum_commission_cny'])
    return (max(minimum,buy*rate)+max(minimum,sell*rate)
            +sell*dec(profile['sell_stamp_rate'])
            +(buy+sell)*dec(profile['transfer_rate_each_side']))


def calculate(code, entry, stop, target, master=None, profile=None, held_value=0,
              available_cash=None, intended_date=None, max_entry=None):
    profile = profile or load_json(ROOT/'references'/'profile.json')
    if profile.get('allowed_exchange')!='SZSE' or profile.get('allowed_board')!='MAIN' or profile.get('chinext_allowed') is not False:
        raise ValueError('首版固定深市主板，不能用配置绕过创业板限制')
    eligibility = security_check(code,(master or {}).get(code))
    e,s,t = map(dec,(entry,stop,target))
    if e<=0 or not s<e<t or s<=0:
        raise ValueError('需满足0<失效价<买入价<目标价')
    ceiling = dec(max_entry) if max_entry is not None else e
    if ceiling<e or ceiling>=t:
        raise ValueError('最高买入价应不低于计划价且低于目标价')
    for v in (e,s,t,ceiling):
        if v != v.quantize(Decimal('0.01')):
            raise ValueError('A股价格精度为0.01元')
    capital = dec(profile['capital_cny'])
    held = dec(held_value)
    cash = dec(available_cash) if available_cash is not None else capital-held
    if capital<=0 or held<0 or cash<0 or held>capital or cash>capital:
        raise ValueError('账户资金或已持仓金额不合法')
    cap = min(dec(profile['max_single_position_cny']),
              capital*dec(profile['max_total_position_fraction'])-held)
    risk_limit = min(dec(profile['risk_budget_cny']),Decimal('60'))
    if risk_limit<=0:
        raise ValueError('风险预算必须大于0')
    slip = dec(profile['slippage_cny_per_share_each_side'])
    if slip<0 or s<=slip:
        raise ValueError('滑点参数不合法')
    choices=[]
    for qty in range(100,max(0,int(cap/ceiling/100))*100+1,100):
        # Risk is calculated at highest permitted fill, not the optimistic entry.
        paid = ceiling*qty
        buy_commission=max(dec(profile['minimum_commission_cny']),paid*dec(profile.get('commission_rate') or 0))
        required_cash=paid+buy_commission+paid*dec(profile['transfer_rate_each_side'])
        cost_stop=fee(paid,s*qty,profile)
        cost_target=fee(paid,t*qty,profile)
        slippage=slip*qty*2
        risk=(ceiling-s)*qty+cost_stop+slippage
        reward=(t-ceiling)*qty-cost_target-slippage
        rr=reward/risk
        if required_cash<=cash and risk<=risk_limit and rr>=dec(profile['min_net_reward_risk']):
            choices.append({'quantity':qty,'stock_value_cny':money(paid),
                'required_cash_cny':money(required_cash),'position_fraction':float(paid/capital),
                'planned_risk_cny':money(risk),'potential_net_reward_cny':money(reward),
                'net_reward_risk':round(float(rr),3),'fees_at_stop_cny':money(cost_stop),
                'fees_at_target_cny':money(cost_target),'slippage_allowance_cny':money(slippage)})
    planned_day=dt.date.fromisoformat(intended_date) if intended_date else now().date()
    days=session_dates(planned_day,5)
    reasons=[]
    if not eligibility['eligible']:
        reasons.append(eligibility['reason'])
    if not profile.get('fees_confirmed') or profile.get('commission_rate') is None:
        reasons.append('完整费率未确认，计算仅为费用假设')
    if not choices:
        reasons.append('没有满足整手、现金、仓位、含费滑点风险和净赔率的数量')
    return {'code':code,'generated_at':now().isoformat(),'plan_status':'draft',
            'eligibility':eligibility,'entry':float(e),'max_entry':float(ceiling),
            'stop':float(s),'target':float(t),'feasible_sizes':choices,
            'provisional_buy_date':days[0],'first_sell_date':days[1],
            'latest_exit_date':days[4],'expiry':'仅拟买入日有效；首笔实际成交后重算五日持有期',
            'blockers':reasons,'calculation_passed':not reasons,
            'execution_ready':False,
            'required_checks':['最新券商行情与可用资金','结构/板块/公告证据','用户人工确认入场',
                               '真实成交数量和可卖日期','条件单委托价格、有效期及互斥支持'],
            'alerts':{'entry':'提醒后人工确认，不能触价盲买','stop':'仅可卖数量；跳空/跌停可能无法成交',
                      'target':'成交后核查并取消残留止损单','time':'第2日复核；第5日计划退出，未成交记异常'},
            'risk_warning':'计划风险不是损失上限；T+1、跳空、停牌、跌停可令损失扩大'}


def journal_append(path, event):
    """Append only, local user-selected path. Never infer fills from alerts."""
    path=Path(path)
    kind=event.get('type')
    if kind not in ('plan','buy_fill','sell_fill','deposit','withdrawal','cancel','execution_error'):
        raise ValueError('未知事件类型')
    moment=dt.datetime.fromisoformat(event['time'])
    if moment.tzinfo is None or moment>now():
        raise ValueError('事件时间须含时区且不在未来')
    history=[]
    if path.exists():
        history=[json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
    if not event.get('id'):
        raise ValueError('必须提供稳定唯一事件id，防止重复登记')
    if any(x.get('id')==event['id'] for x in history):
        raise ValueError('事件id已经登记，不重复记账')
    if kind in ('deposit','withdrawal'):
        if dec(event['amount_cny'])<=0:
            raise ValueError('出入金金额须为正')
        event['counts_as_trading_pnl']=False
    if kind in ('buy_fill','sell_fill'):
        code=event['code']
        if not isinstance(code,str) or len(code)!=6 or not code.isdigit():
            raise ValueError('成交代码须为六位字符串')
        qty=event['quantity']
        if isinstance(qty,bool) or not isinstance(qty,int) or qty<=0:
            raise ValueError('实际成交数量必须为正整数')
        # Partial fills need not be multiples of 100; original order must be valid.
        if dec(event['price'])<=0 or dec(event['fees_cny'])<0:
            raise ValueError('成交价或实际费用不合法')
        if not event.get('plan_id'):
            raise ValueError('成交须关联计划；临时交易先登记独立计划编号')
        buys=[x for x in history if x['type']=='buy_fill' and x.get('plan_id')==event['plan_id'] and x.get('code')==code]
        sells=[x for x in history if x['type']=='sell_fill' and x.get('plan_id')==event['plan_id'] and x.get('code')==code]
        if kind=='buy_fill':
            first=min([dt.datetime.fromisoformat(x['time']).astimezone(TZ).date() for x in buys]+[moment.astimezone(TZ).date()])
            event['latest_exit_date']=session_dates(first,5)[4]
            if first!=moment.astimezone(TZ).date() and moment.astimezone(TZ).date().isoformat()>event['latest_exit_date']:
                raise ValueError('原计划已到期；加仓不能重置持有期')
        else:
            if any(dt.datetime.fromisoformat(x['time'])>moment for x in buys+sells):
                raise ValueError('该计划已有更晚的成交，先按时间顺序核对记录')
            available=sum(x['quantity'] for x in buys if dt.datetime.fromisoformat(x['time']).astimezone(TZ).date()<moment.astimezone(TZ).date())-sum(x['quantity'] for x in sells)
            if qty>available:
                raise ValueError('卖出超过已登记可卖数量（T+1/成交记录缺失）')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as f:
        f.write(json.dumps(event,ensure_ascii=False,allow_nan=False)+'\n')
    return {'recorded':event,'journal':str(path.resolve()),'broker_action':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('calculate')
    c.add_argument('code'); c.add_argument('--entry',required=True); c.add_argument('--stop',required=True)
    c.add_argument('--target',required=True); c.add_argument('--max-entry'); c.add_argument('--master')
    c.add_argument('--profile'); c.add_argument('--held-value',default='0'); c.add_argument('--available-cash')
    c.add_argument('--buy-date')
    j=sub.add_parser('record')
    j.add_argument('--journal',required=True); j.add_argument('--event',required=True)
    a=p.parse_args()
    try:
        if a.command=='record':
            result=journal_append(a.journal,load_json(a.event))
        else:
            result=calculate(a.code,a.entry,a.stop,a.target,
                load_json(a.master) if a.master else None,load_json(a.profile) if a.profile else None,
                a.held_value,a.available_cash,a.buy_date,a.max_entry)
        emit({'ok':True,'result':result})
    except Exception as exc:
        emit({'ok':False,'error':str(exc)})
        raise SystemExit(1)


if __name__=='__main__':
    main()
