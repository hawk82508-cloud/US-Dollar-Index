import os
import re
import sys
import json
import datetime
import requests
import pandas as pd
import numpy as np

DAILY_CSV = 'raw_daily.csv'
WEEKLY_CSV = 'raw_weekly.csv'
MONTHLY_CSV = 'raw_monthly.csv'
INDEX_HTML = 'index.html'

def fetch_latest_dxy():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    }

    # Engine 1: Yahoo Finance Global CDN (query1 & query2 fallback) for DX-Y.NYB / DX=F
    for sym in ['DX-Y.NYB', 'DX%3DF']:
        for host in ['query1.finance.yahoo.com', 'query2.finance.yahoo.com']:
            try:
                y_url = f"https://{host}/v8/finance/chart/{sym}?interval=1d&range=5d"
                r = requests.get(y_url, headers=headers, timeout=12)
                if r.status_code == 200:
                    res = r.json()
                    result = res['chart']['result'][0]
                    timestamps = result['timestamp']
                    quote = result['indicators']['quote'][0]
                    gmtoffset = result.get('meta', {}).get('gmtoffset', -14400)
                    tz_us = datetime.timezone(datetime.timedelta(seconds=gmtoffset))

                    for i in range(len(timestamps) - 1, -1, -1):
                        c = quote['close'][i]
                        o = quote['open'][i]
                        h = quote['high'][i]
                        l = quote['low'][i]
                        v = quote.get('volume', [0])[i] if quote.get('volume') else 0

                        if c is not None and o is not None and not np.isnan(c):
                            d_dt = datetime.datetime.fromtimestamp(timestamps[i], tz=tz_us).date()
                            if d_dt.weekday() >= 5:
                                continue
                            d_str = d_dt.strftime('%Y-%m-%d')
                            vol_val = round(float(v) / 100000000.0, 2) if v else 0.0
                            print(f"Yahoo Finance ({host} / {sym}): {d_str} O={o:.2f}, H={h:.2f}, L={l:.2f}, C={c:.2f}")
                            return {
                                '時間': d_str,
                                '開盤價': round(float(o), 2),
                                '最高價': round(float(max(h, o, c)), 2),
                                '最低價': round(float(min(l, o, c)), 2),
                                '收盤價': round(float(c), 2),
                                '成交量': vol_val
                            }
            except Exception as e:
                print(f"Yahoo Finance ({host} / {sym}) Notice: {e}")

    # Engine 2: Stooq International Financial Data Feed (dx.f / ^dxy)
    for stooq_sym in ['dx.f', '^dxy']:
        try:
            s_url = f"https://stooq.com/q/d/l/?s={stooq_sym}&i=d"
            r = requests.get(s_url, headers=headers, timeout=12)
            if r.status_code == 200 and 'Date' in r.text:
                lines = [line.strip() for line in r.text.strip().split('\n') if line.strip()]
                if len(lines) >= 2:
                    last_line = lines[-1].split(',')
                    d_str = last_line[0]
                    o = float(last_line[1])
                    h = float(last_line[2])
                    l = float(last_line[3])
                    c = float(last_line[4])
                    v = float(last_line[5]) if len(last_line) > 5 and last_line[5] != '' else 0.0
                    print(f"Stooq ({stooq_sym}): {d_str} O={o:.2f}, H={h:.2f}, L={l:.2f}, C={c:.2f}")
                    return {
                        '時間': d_str,
                        '開盤價': round(o, 2),
                        '最高價': round(max(h, o, c), 2),
                        '最低價': round(min(l, o, c), 2),
                        '收盤價': round(c, 2),
                        '成交量': round(v / 100000000.0, 2) if v > 0 else 0.0
                    }
        except Exception as e:
            print(f"Stooq ({stooq_sym}) Notice: {e}")

    # Engine 3: CNBC Real-Time Quote API (.DXY)
    try:
        cnbc_url = "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols=.DXY&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1"
        r = requests.get(cnbc_url, headers=headers, timeout=12)
        if r.status_code == 200:
            q = r.json()['FormattedQuoteResult']['FormattedQuote'][0]
            c = float(str(q['last']).replace(',', ''))
            o = float(str(q.get('open', c)).replace(',', ''))
            h = float(str(q.get('high', c)).replace(',', ''))
            l = float(str(q.get('low', c)).replace(',', ''))
            tz_ny = datetime.timezone(datetime.timedelta(hours=-4))
            d_str = datetime.datetime.now(tz=tz_ny).date().strftime('%Y-%m-%d')
            print(f"CNBC API (.DXY): {d_str} C={c:.2f}")
            return {
                '時間': d_str,
                '開盤價': round(o, 2),
                '最高價': round(max(h, o, c), 2),
                '最低價': round(min(l, o, c), 2),
                '收盤價': round(c, 2),
                '成交量': 0.0
            }
    except Exception as e:
        print(f"CNBC Notice: {e}")

    return None

def update_csv_datasets():
    if not os.path.exists(DAILY_CSV):
        return

    latest_data = fetch_latest_dxy()
    if not latest_data:
        print("Notice: No live network data retrieved; calculating with existing CSV.")
        return

    target_date = str(latest_data['時間'])
    daily_df = pd.read_csv(DAILY_CSV)

    if target_date not in daily_df['時間'].astype(str).values:
        prev_close = float(daily_df.iloc[-1]['收盤價'])
        chg = round(latest_data['收盤價'] - prev_close, 2)
        pct = round((chg / prev_close) * 100.0, 2)
        latest_data['漲跌'] = chg
        latest_data['漲跌幅'] = pct
        print(f"Appending new date {target_date}: Close={latest_data['收盤價']} ({chg:+.2f}, {pct:+.2f}%)")
        daily_df = pd.concat([daily_df, pd.DataFrame([latest_data])], ignore_index=True)
        daily_df.to_csv(DAILY_CSV, index=False)
    else:
        idx = daily_df[daily_df['時間'].astype(str) == target_date].index[0]
        prev_close = float(daily_df.iloc[idx - 1]['收盤價']) if idx > 0 else float(latest_data['開盤價'])
        daily_df.at[idx, '開盤價'] = latest_data['開盤價']
        daily_df.at[idx, '最高價'] = max(float(daily_df.at[idx, '最高價']), float(latest_data['最高價']))
        daily_df.at[idx, '最低價'] = min(float(daily_df.at[idx, '最低價']), float(latest_data['最低價']))
        daily_df.at[idx, '收盤價'] = latest_data['收盤價']
        chg = round(float(latest_data['收盤價']) - prev_close, 2)
        pct = round((chg / prev_close) * 100.0, 2)
        daily_df.at[idx, '漲跌'] = chg
        daily_df.at[idx, '漲跌幅'] = pct
        if latest_data.get('成交量', 0) > 0:
            daily_df.at[idx, '成交量'] = latest_data['成交量']
        daily_df.to_csv(DAILY_CSV, index=False)

    # Update Weekly CSV (matching by Monday of the week, keeping Friday date label convention)
    if os.path.exists(WEEKLY_CSV):
        weekly_df = pd.read_csv(WEEKLY_CSV)
        target_dt = datetime.datetime.strptime(target_date, '%Y-%m-%d').date()
        mon_dt = target_dt - datetime.timedelta(days=target_dt.weekday())
        fri_dt = mon_dt + datetime.timedelta(days=4)
        fri_str = fri_dt.strftime('%Y-%m-%d')

        matched_w_idx = None
        for w_idx, r in weekly_df.iterrows():
            r_dt = datetime.datetime.strptime(str(r['時間']), '%Y-%m-%d').date()
            r_mon = r_dt - datetime.timedelta(days=r_dt.weekday())
            if r_mon == mon_dt:
                matched_w_idx = w_idx
                break

        if matched_w_idx is None:
            prev_w_close = float(weekly_df.iloc[-1]['收盤價'])
            chg = round(latest_data['收盤價'] - prev_w_close, 2)
            pct = round((chg / prev_w_close) * 100.0, 2)
            w_row = {
                '時間': fri_str,
                '開盤價': latest_data['開盤價'],
                '最高價': latest_data['最高價'],
                '最低價': latest_data['最低價'],
                '收盤價': latest_data['收盤價'],
                '漲跌': chg,
                '漲跌幅': pct,
                '成交量': latest_data.get('成交量', 0.0)
            }
            weekly_df = pd.concat([weekly_df, pd.DataFrame([w_row])], ignore_index=True)
        else:
            prev_w_close = float(weekly_df.iloc[matched_w_idx - 1]['收盤價']) if matched_w_idx > 0 else float(weekly_df.at[matched_w_idx, '開盤價'])
            weekly_df.at[matched_w_idx, '最高價'] = max(float(weekly_df.at[matched_w_idx, '最高價']), float(latest_data['最高價']))
            weekly_df.at[matched_w_idx, '最低價'] = min(float(weekly_df.at[matched_w_idx, '最低價']), float(latest_data['最低價']))
            weekly_df.at[matched_w_idx, '收盤價'] = latest_data['收盤價']
            chg = round(float(latest_data['收盤價']) - prev_w_close, 2)
            pct = round((chg / prev_w_close) * 100.0, 2)
            weekly_df.at[matched_w_idx, '漲跌'] = chg
            weekly_df.at[matched_w_idx, '漲跌幅'] = pct
        weekly_df.to_csv(WEEKLY_CSV, index=False)

    # Update Monthly CSV
    if os.path.exists(MONTHLY_CSV):
        monthly_df = pd.read_csv(MONTHLY_CSV)
        ym_str = target_date[:7]
        m_matches = monthly_df[monthly_df['時間'].astype(str).str.startswith(ym_str)].index
        if len(m_matches) > 0:
            m_idx = m_matches[0]
            prev_m_close = float(monthly_df.iloc[m_idx - 1]['收盤價']) if m_idx > 0 else float(monthly_df.at[m_idx, '開盤價'])
            monthly_df.at[m_idx, '最高價'] = max(float(monthly_df.at[m_idx, '最高價']), float(latest_data['最高價']))
            monthly_df.at[m_idx, '最低價'] = min(float(monthly_df.at[m_idx, '最低價']), float(latest_data['最低價']))
            monthly_df.at[m_idx, '收盤價'] = latest_data['收盤價']
            chg = round(float(latest_data['收盤價']) - prev_m_close, 2)
            pct = round((chg / prev_m_close) * 100.0, 2)
            monthly_df.at[m_idx, '漲跌'] = chg
            monthly_df.at[m_idx, '漲跌幅'] = pct
        else:
            prev_m_close = float(monthly_df.iloc[-1]['收盤價'])
            chg = round(latest_data['收盤價'] - prev_m_close, 2)
            pct = round((chg / prev_m_close) * 100.0, 2)
            m_row = {
                '時間': f"{ym_str}-01",
                '開盤價': latest_data['開盤價'],
                '最高價': latest_data['最高價'],
                '最低價': latest_data['最低價'],
                '收盤價': latest_data['收盤價'],
                '漲跌': chg,
                '漲跌幅': pct,
                '成交量': latest_data.get('成交量', 0.0)
            }
            monthly_df = pd.concat([monthly_df, pd.DataFrame([m_row])], ignore_index=True)
        monthly_df.to_csv(MONTHLY_CSV, index=False)

def recalculate_and_build(skip_network=False):
    if not skip_network:
        update_csv_datasets()

    daily_df = pd.read_csv(DAILY_CSV)
    weekly_df = pd.read_csv(WEEKLY_CSV)
    monthly_df = pd.read_csv(MONTHLY_CSV)

    for df in [daily_df, weekly_df, monthly_df]:
        df['high_12'] = df['最高價'].rolling(12).max().round(2)
        df['low_12'] = df['最低價'].rolling(12).min().round(2)
        df['point1'] = ((df['high_12'] * 2 + df['low_12']) / 3.0).round(2)
        df['point2'] = ((df['high_12'] + df['low_12'] * 2) / 3.0).round(2)

    weekly_lookup = []
    for idx, r in weekly_df.iterrows():
        w_dt = datetime.datetime.strptime(str(r['時間']), '%Y-%m-%d').date()
        mon_dt = w_dt - datetime.timedelta(days=w_dt.weekday())
        weekly_lookup.append({
            'start_date': mon_dt.strftime('%Y-%m-%d'),
            'high_12': float(r['high_12']) if not pd.isna(r['high_12']) else None,
            'low_12': float(r['low_12']) if not pd.isna(r['low_12']) else None,
            'point1': float(r['point1']) if not pd.isna(r['point1']) else None,
            'point2': float(r['point2']) if not pd.isna(r['point2']) else None
        })

    monthly_lookup = []
    for idx, r in monthly_df.iterrows():
        monthly_lookup.append({
            'ym': str(r['時間'])[:7],
            'start_date': str(r['時間']),
            'high_12': float(r['high_12']) if not pd.isna(r['high_12']) else None,
            'low_12': float(r['low_12']) if not pd.isna(r['low_12']) else None,
            'point1': float(r['point1']) if not pd.isna(r['point1']) else None,
            'point2': float(r['point2']) if not pd.isna(r['point2']) else None
        })

    def get_weekly_point(date_str):
        matched = None
        for w in weekly_lookup:
            if date_str >= w['start_date']:
                matched = w
            else:
                break
        if matched:
            return matched['point1'], matched['point2']
        return None, None

    def get_monthly_point(date_str):
        d_ym = date_str[:7]
        matched = None
        for m in monthly_lookup:
            if m['ym'] == d_ym:
                matched = m
                break
            elif date_str >= m['start_date']:
                matched = m
        if matched:
            return matched['point1'], matched['point2']
        return None, None

    daily_list = []
    multi_list = []

    for idx, r in daily_df.iterrows():
        d_str = str(r['時間'])
        p1_d = float(r['point1']) if not pd.isna(r['point1']) else None
        p2_d = float(r['point2']) if not pd.isna(r['point2']) else None
        h12_d = float(r['high_12']) if not pd.isna(r['high_12']) else None
        l12_d = float(r['low_12']) if not pd.isna(r['low_12']) else None

        w_p1, w_p2 = get_weekly_point(d_str)
        m_p1, m_p2 = get_monthly_point(d_str)

        item_base = {
            'date': d_str,
            'open': float(r['開盤價']),
            'high': float(r['最高價']),
            'low': float(r['最低價']),
            'close': float(r['收盤價']),
            'change': float(r['漲跌']) if '漲跌' in r and not pd.isna(r['漲跌']) else round(float(r['收盤價']) - float(r['開盤價']), 2),
            'change_pct': float(r['漲跌幅']) if '漲跌幅' in r and not pd.isna(r['漲跌幅']) else round((float(r['收盤價']) - float(r['開盤價'])) / float(r['開盤價']) * 100, 2),
            'volume': float(r['成交量']) if '成交量' in r and not pd.isna(r['成交量']) else 0.0,
            'high_12': h12_d,
            'low_12': l12_d,
            'point1': p1_d,
            'point2': p2_d,
            'is_future': False
        }
        daily_list.append(item_base)

        multi_item = {
            **item_base,
            'w_point1': w_p1,
            'w_point2': w_p2,
            'm_point1': m_p1,
            'm_point2': m_p2
        }
        multi_list.append(multi_item)

    weekly_list = []
    for idx, r in weekly_df.iterrows():
        weekly_list.append({
            'label': str(r['時間']),
            'date': str(r['時間']),
            'open': float(r['開盤價']),
            'high': float(r['最高價']),
            'low': float(r['最低價']),
            'close': float(r['收盤價']),
            'change': float(r['漲跌']) if '漲跌' in r and not pd.isna(r['漲跌']) else 0.0,
            'change_pct': float(r['漲跌幅']) if '漲跌幅' in r and not pd.isna(r['漲跌幅']) else 0.0,
            'volume': float(r['成交量']) if '成交量' in r and not pd.isna(r['成交量']) else 0.0,
            'high_12': float(r['high_12']) if not pd.isna(r['high_12']) else None,
            'low_12': float(r['low_12']) if not pd.isna(r['low_12']) else None,
            'point1': float(r['point1']) if not pd.isna(r['point1']) else None,
            'point2': float(r['point2']) if not pd.isna(r['point2']) else None,
            'is_future': False
        })

    monthly_list = []
    for idx, r in monthly_df.iterrows():
        monthly_list.append({
            'month': str(r['時間'])[:7],
            'date': str(r['時間'])[:7],
            'open': float(r['開盤價']),
            'high': float(r['最高價']),
            'low': float(r['最低價']),
            'close': float(r['收盤價']),
            'change': float(r['漲跌']) if '漲跌' in r and not pd.isna(r['漲跌']) else 0.0,
            'change_pct': float(r['漲跌幅']) if '漲跌幅' in r and not pd.isna(r['漲跌幅']) else 0.0,
            'volume': float(r['成交量']) if '成交量' in r and not pd.isna(r['成交量']) else 0.0,
            'high_12': float(r['high_12']) if not pd.isna(r['high_12']) else None,
            'low_12': float(r['low_12']) if not pd.isna(r['low_12']) else None,
            'point1': float(r['point1']) if not pd.isna(r['point1']) else None,
            'point2': float(r['point2']) if not pd.isna(r['point2']) else None,
            'is_future': False
        })

    last_11_d = daily_df.tail(11)
    h11_d = round(float(last_11_d['最高價'].max()), 2)
    l11_d = round(float(last_11_d['最低價'].min()), 2)
    p1_d_future = round((h11_d * 2 + l11_d) / 3.0, 2)
    p2_d_future = round((h11_d + l11_d * 2) / 3.0, 2)

    last_date = datetime.datetime.strptime(str(daily_df.iloc[-1]['時間']), '%Y-%m-%d').date()
    next_day = last_date + datetime.timedelta(days=1)
    while next_day.weekday() >= 5:
        next_day += datetime.timedelta(days=1)
    next_day_label = f"{next_day.strftime('%Y-%m-%d')} (次日預測)"

    daily_future = {
        'label': next_day_label,
        'date': next_day_label,
        'open': None, 'high': None, 'low': None, 'close': None, 'volume': None,
        'high_12': h11_d,
        'low_12': l11_d,
        'point1': p1_d_future,
        'point2': p2_d_future,
        'is_future': True
    }

    last_11_w = weekly_df.tail(11)
    h11_w = round(float(last_11_w['最高價'].max()), 2)
    l11_w = round(float(last_11_w['最低價'].min()), 2)
    p1_w_future = round((h11_w * 2 + l11_w) / 3.0, 2)
    p2_w_future = round((h11_w + l11_w * 2) / 3.0, 2)

    weekly_future = {
        'label': '次週預測',
        'date': '次週預測',
        'open': None, 'high': None, 'low': None, 'close': None, 'volume': None,
        'high_12': h11_w,
        'low_12': l11_w,
        'point1': p1_w_future,
        'point2': p2_w_future,
        'is_future': True
    }

    last_11_m = monthly_df.tail(11)
    h11_m = round(float(last_11_m['最高價'].max()), 2)
    l11_m = round(float(last_11_m['最低價'].min()), 2)
    p1_m_future = round((h11_m * 2 + l11_m) / 3.0, 2)
    p2_m_future = round((h11_m + l11_m * 2) / 3.0, 2)

    monthly_future = {
        'label': '次月預測',
        'month': '次月預測',
        'date': '次月預測',
        'open': None, 'high': None, 'low': None, 'close': None, 'volume': None,
        'high_12': h11_m,
        'low_12': l11_m,
        'point1': p1_m_future,
        'point2': p2_m_future,
        'is_future': True
    }

    multi_future = {
        'label': f"{next_day.strftime('%Y-%m-%d')} (次期前瞻)",
        'date': f"{next_day.strftime('%Y-%m-%d')} (次期前瞻)",
        'open': None, 'high': None, 'low': None, 'close': None, 'volume': None,
        'high_12': h11_d,
        'low_12': l11_d,
        'point1': p1_d_future,
        'point2': p2_d_future,
        'w_point1': p1_w_future,
        'w_point2': p2_w_future,
        'm_point1': p1_m_future,
        'm_point2': p2_m_future,
        'is_future': True
    }

    payload = {
        'daily': daily_list,
        'daily_future': daily_future,
        'weekly': weekly_list,
        'weekly_future': weekly_future,
        'monthly': monthly_list,
        'monthly_future': monthly_future,
        'multi': multi_list,
        'multi_future': multi_future
    }

    payload_json = json.dumps(payload, ensure_ascii=False)

    with open(INDEX_HTML, 'r', encoding='utf-8') as f:
        html = f.read()

    new_html = re.sub(
        r'const appPayload = (\{.*?\});',
        lambda m: f'const appPayload = {payload_json};',
        html,
        flags=re.DOTALL
    )

    with open(INDEX_HTML, 'w', encoding='utf-8') as f:
        f.write(new_html)

    print(f"Update completed: {INDEX_HTML} generated with {len(daily_list)} daily bars, {len(weekly_list)} weekly bars, {len(monthly_list)} monthly bars.")

if __name__ == '__main__':
    try:
        skip_net = '--offline' in sys.argv
        recalculate_and_build(skip_network=skip_net)
    except Exception as e:
        print(f"Error in recalculate_and_build: {e}")
        sys.exit(0)
