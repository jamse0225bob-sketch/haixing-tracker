import akshare as ak
import requests
import pandas as pd
import datetime

# ⚠️ 注意：请把下方双引号里的内容，替换为你阶段一保存的 Google 接收端网址
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyHOcngO7GotE7CYpyxM2_bjg5vDbAZnGAhYRera95Tu56IHBs430qcOkhJ6DuCvF6P/exec"

def get_haixing_data():
    symbol = "603556"
    print(f"[{datetime.datetime.now()}] 开始提取海兴电力({symbol})行情数据...")
    
    # 1. 抓取日 K 线数据（前复权 qfq，保证均线精准）
    df_hist = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
    
    # 获取最新交易日数据与近 60 日均价
    df_last_60 = df_hist.tail(60)
    latest_close = float(df_hist['收盘'].iloc[-1])
    ma60 = round(float(df_last_60['收盘'].mean()), 2)
    trade_date = str(df_hist['日期'].iloc[-1])
    
    # 2. 抓取估值指标 (PE-TTM)
    df_indicator = ak.stock_a_lg_indicator(symbol=symbol)
    pe_ttm = round(float(df_indicator['pe_ttm'].iloc[-1]), 2)
    
    # 3. 组装数据包
    payload = {
        "date": trade_date,
        "close": latest_close,
        "ma60": ma60,
        "pe_ttm": pe_ttm
    }
    
    # 4. 发送到 Google Sheets
    response = requests.post(WEB_APP_URL, json=payload)
    print(f"发送状态: {response.text}")

if __name__ == "__main__":
    get_haixing_data()
