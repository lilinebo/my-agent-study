"""Deterministic regression tests for data quality and financial constraints."""
import datetime as dt
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import core
import quotes
import research
import trade_plan

FIXED=dt.datetime(2026,10,22,10,0,tzinfo=core.TZ)


def row(stamp=None):
    return {'f58':'测试股票','f57':'000837','f43':10,'f170':0,'f48':100000,
            'f86':(stamp or FIXED).timestamp(),'f46':10,'f44':10.1,'f45':9.9,
            'f60':10,'f47':100,'f168':1,'f50':1}


def master(code='000837'):
    return {code:{'code':code,'name':'测试股票','exchange':'SZSE','board':'MAIN',
        'kind':'A_SHARE','listed_date':'2010-01-01','status':'trading','unrestricted':False,
        'checked_at':FIXED.isoformat(),'source_url':'https://investor.szse.cn/'}}


class QualityTests(unittest.TestCase):
    def test_missing_minute_open_is_not_invented(self):
        d={'code':'000837','name':'测试','klines':['2026-10-22 09:31,0,10,10.1,9.9,100,100000']}
        b=research.parse_bars(d,'000837','1',FIXED)[0]
        self.assertIsNone(b['open'])
        self.assertEqual(b['missing_fields'],['open'])
        self.assertEqual(b['close'],10)

    def test_future_clock_is_not_realtime(self):
        q=quotes.normalize(row(FIXED+dt.timedelta(seconds=4)),'000837',received=FIXED,record=master()['000837'])
        self.assertEqual(q['quality'],'clock_skew')
        self.assertLess(q['age_seconds'],0)

    def test_far_future_rejected(self):
        with self.assertRaises(ValueError):
            quotes.normalize(row(FIXED+dt.timedelta(seconds=61)),'000837',received=FIXED)

    def test_fresh_requires_status(self):
        self.assertEqual(quotes.normalize(row(),'000837',received=FIXED)['quality'],'fresh_unconfirmed')
        self.assertEqual(quotes.normalize(row(),'000837',received=FIXED,record=master()['000837'])['quality'],'realtime')

    def test_lunch_does_not_mark_last_trade_realtime(self):
        t=FIXED.replace(hour=11,minute=30)
        self.assertNotEqual(quotes.normalize(row(t),'000837',received=t+dt.timedelta(seconds=30))['quality'],'realtime')

    def test_after_close_unconfirmed(self):
        t=FIXED.replace(hour=15)
        self.assertEqual(quotes.normalize(row(t),'000837',received=t+dt.timedelta(seconds=5))['quality'],'close_unconfirmed')

    def test_previous_date_is_historical(self):
        self.assertEqual(quotes.normalize(row(FIXED-dt.timedelta(days=1)),'000837',received=FIXED)['quality'],'historical')

    def test_ohlcv_preserved(self):
        q=quotes.normalize(row(),'000837',received=FIXED)
        self.assertEqual(q['volume_shares'],10000)
        self.assertEqual(q['open'],10)
        self.assertEqual(q['previous_close'],10)

    def test_inconsistent_percent_rejected(self):
        r=row(); r['f170']=5
        with self.assertRaises(ValueError):
            quotes.normalize(r,'000837',received=FIXED)

    def test_invalid_numbers_rejected(self):
        for value in [True,float('nan'),float('inf'),None]:
            r=row(); r['f43']=value
            with self.assertRaises(ValueError):
                quotes.normalize(r,'000837',received=FIXED)

    def test_bad_high_rejected(self):
        r=row(); r['f44']=9
        with self.assertRaises(ValueError):
            quotes.normalize(r,'000837',received=FIXED)

    def test_index_and_bank_collision(self):
        a={'f12':'000001','f13':0,'f14':'平安银行','f2':10,'f3':0,'f6':100,'f124':FIXED.timestamp(),
           'f15':10.1,'f16':9.9,'f17':10,'f18':10,'f5':100}
        b={**a,'f13':1,'f14':'上证指数'}
        envelope={'payload':{'data':{'diff':[a,b]}}}
        with patch('quotes.request_json',return_value=envelope),patch('quotes.now',return_value=FIXED):
            result=quotes.query(['000001','1.000001'])
        self.assertEqual([q['name'] for q in result['quotes']],['平安银行','上证指数'])

    def test_single_fallback_for_missing_batch_item(self):
        envelope={'payload':{'data':{'diff':[]}}}
        with patch('quotes.request_json',return_value=envelope),patch('quotes.single',return_value=quotes.normalize(row(),'000837',received=FIXED)) as f:
            result=quotes.query(['000837','000837'])
        self.assertEqual(f.call_count,1)
        self.assertEqual(result['success_count'],1)


class CalendarTests(unittest.TestCase):
    def test_holiday_weekend_and_open(self):
        self.assertFalse(core.trading_day(dt.date(2026,10,1)))
        self.assertFalse(core.trading_day(dt.date(2026,10,10)))
        self.assertTrue(core.trading_day(dt.date(2026,10,22)))

    def test_unknown_year_fails_closed(self):
        self.assertIsNone(core.trading_day(dt.date(2027,1,4)))
        with self.assertRaises(ValueError):
            core.session_dates(dt.date(2026,12,31),5)

    def test_holding_period_skips_holidays(self):
        self.assertEqual(core.session_dates(dt.date(2026,9,24),5),
                         ['2026-09-24','2026-09-28','2026-09-29','2026-09-30','2026-10-08'])


class BarsTests(unittest.TestCase):
    def data(self,lines):
        return {'code':'000837','name':'测试股票','klines':lines}

    def test_today_provisional_and_prior_complete(self):
        b=research.parse_bars(self.data(['2026-10-21,10,10,11,9,100,100000',
                                        '2026-10-22,10,10,11,9,100,100000']),'000837','day',FIXED)
        self.assertTrue(b[0]['completed']); self.assertFalse(b[1]['completed'])

    def test_minute_completion_and_units(self):
        b=research.parse_bars(self.data(['2026-10-22 09:50,10,10,11,9,100,100000',
                                        '2026-10-22 09:55,10,10,11,9,100,100000']),'000837','5',FIXED)
        self.assertTrue(b[0]['completed']); self.assertFalse(b[1]['completed'])
        self.assertEqual(b[0]['volume_shares'],10000)

    def test_duplicates_future_and_ohlc_rejected(self):
        for lines in [['2026-10-21,10,10,11,9,100,1']*2,
                      ['2026-10-23,10,10,11,9,100,1'],['2026-10-21,10,10,9,9,100,1']]:
            with self.assertRaises(ValueError):
                research.parse_bars(self.data(lines),'000837','day',FIXED)


class HTTPTests(unittest.TestCase):
    def test_404_not_retried(self):
        error=urllib.error.HTTPError('https://example.com',404,'missing',{},None)
        with patch('core.urllib.request.urlopen',side_effect=error) as f:
            with self.assertRaises(urllib.error.HTTPError):
                core.request_json('https://example.com')
        self.assertEqual(f.call_count,1)

    def test_disconnect_bounded_and_cache_labeled(self):
        with tempfile.TemporaryDirectory() as directory:
            key=core.hashlib.sha256(('testhttps://example.comNone').encode()).hexdigest()
            Path(directory,key+'.json').write_text(json.dumps({'payload':{'data':{}},
                'response_received_at':FIXED.isoformat()}),encoding='utf-8')
            with patch('core.urllib.request.urlopen',side_effect=OSError('offline')) as f,patch('core.time.sleep'):
                e=core.request_json('https://example.com',cache_dir=directory,cache_key='test')
            self.assertEqual(f.call_count,3)
            self.assertEqual(e['cache_status'],'stale_fallback')
            self.assertEqual(e['cached_at'],FIXED.isoformat())


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.p=core.load_json(core.ROOT/'references'/'profile.json')
        self.p.update(fees_confirmed=True,commission_rate=0.0003)
        self.clock=patch('core.now',return_value=FIXED); self.clock.start(); self.addCleanup(self.clock.stop)
        self.clock2=patch('trade_plan.now',return_value=FIXED); self.clock2.start(); self.addCleanup(self.clock2.stop)

    def calc(self,code='000837',stop='9.80',max_entry=None):
        return trade_plan.calculate(code,'10',stop,'10.80',master(code),self.p,intended_date='2026-10-22',max_entry=max_entry)

    def test_chinext_and_other_markets_blocked(self):
        for c in ('300750','301001','600519','399006'):
            self.assertFalse(self.calc(c)['eligibility']['eligible'])

    def test_mainboard_needs_real_master(self):
        self.assertFalse(core.security_check('000837')['eligible'])
        m=master()['000837']; m['board']='CHINEXT'
        self.assertFalse(core.security_check('000837',m)['eligible'])

    def test_costs_slippage_and_round_lots(self):
        r=self.calc()
        self.assertTrue(r['calculation_passed'])
        self.assertFalse(r['execution_ready'])
        best=r['feasible_sizes'][-1]
        self.assertEqual(best['quantity'],200)
        self.assertGreater(best['planned_risk_cny'],40+10)
        self.assertLessEqual(best['planned_risk_cny'],60)
        self.assertEqual(r['latest_exit_date'],'2026-10-28')

    def test_too_wide_stop_not_squeezed(self):
        self.assertEqual(self.calc(stop='9.00')['feasible_sizes'],[])

    def test_ceiling_not_optimistic_entry(self):
        self.assertEqual(self.calc(max_entry='10.50')['feasible_sizes'],[])

    def test_fee_unknown_is_blocker(self):
        self.p['fees_confirmed']=False
        self.assertFalse(self.calc()['calculation_passed'])

    def test_quantity_cash_includes_commission(self):
        r=trade_plan.calculate('000837','10','9.8','10.8',master(),self.p,available_cash=1000,intended_date='2026-10-22')
        self.assertEqual(r['feasible_sizes'],[])

    def test_journal_t1_duplicate_and_withdrawal(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory,'journal.jsonl')
            b={'id':'b1','type':'buy_fill','time':'2026-10-20T10:00:00+08:00',
               'plan_id':'p1','code':'000837','quantity':100,'price':10,'fees_cny':5}
            trade_plan.journal_append(p,b)
            with self.assertRaises(ValueError):
                trade_plan.journal_append(p,b)
            s={**b,'id':'s1','type':'sell_fill','time':'2026-10-20T14:00:00+08:00'}
            with self.assertRaises(ValueError):
                trade_plan.journal_append(p,s)
            s['time']='2026-10-21T10:00:00+08:00'
            trade_plan.journal_append(p,s)
            w={'id':'w1','type':'withdrawal','time':'2026-10-21T11:00:00+08:00','amount_cny':2000}
            self.assertFalse(trade_plan.journal_append(p,w)['recorded']['counts_as_trading_pnl'])

    def test_additional_fill_does_not_extend_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory,'journal.jsonl')
            b={'id':'b1','type':'buy_fill','time':'2026-10-20T10:00:00+08:00',
               'plan_id':'p1','code':'000837','quantity':100,'price':10,'fees_cny':5}
            first=trade_plan.journal_append(p,b)['recorded']['latest_exit_date']
            b2={**b,'id':'b2','time':'2026-10-21T10:00:00+08:00'}
            self.assertEqual(trade_plan.journal_append(p,b2)['recorded']['latest_exit_date'],first)


if __name__=='__main__':
    unittest.main()
