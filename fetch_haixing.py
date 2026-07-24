import os
import requests
import pandas as pd
import datetime
import tushare as ts

# 你的 Google Sheets 接收端网址
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxyPTllOdzZhqFVG-I263Zzi8Pt_VQPRFshIUMC_aop_rVXayG08BYAOvPYmU9JZhyR/exec" # 请确保这里填入真实的网址

def get_haixing_data():
    symbol = "603556.SH" # Tushare 的代码后缀规则
    
    # 从 GitHub 的保密环境变量中读取 Token，绝不将密码硬编码在文件中
    tushare_token = os.environ.get("TUSHARE_TOKEN")
    if not tushare_token:
        raise ValueError("致命错误：未找到 TUSHARE_TOKEN 环境变量")
    
    ts.set_token(tushare_token)
    pro = ts.pro_api()
    
    trade_date_str = datetime.datetime.now().strftime('%Y%m%d')
    print(f"[{datetime.datetime.now()}] 开始通过 Tushare 提取海兴电力({symbol})行情...")
    
    # 1. 抓取最新的日线数据 (包含收盘价，无视反爬虫)
    df_daily = pro.daily(ts_code=symbol, end_date=trade_date_str, limit=60)
    
    if df_daily.empty:
        raise ValueError("未能抓取到交易数据，可能尚未更新或非交易日")

    latest_close = float(df_daily['close'].iloc[0]) # 列表倒序，索引 0 为最新
    ma60 = round(float(df_daily['close'].mean()), 2)
    trade_date = str(df_daily['trade_date'].iloc[0])
    
    # 2. 抓取每日估值指标 (PE-TTM) - 增加防频繁测试的容错装甲
    try:
        df_basic = pro.daily_basic(ts_code=symbol, end_date=trade_date_str, fields='ts_code,trade_date,pe_ttm')
        if not df_basic.empty:
            pe_ttm = round(float(df_basic['pe_ttm'].iloc[0]), 2)
        else:
            pe_ttm = "数据未生成"
    except Exception as e:
        print(f"警告: 估值接口受限 ({e})。启动降级机制，舍弃 PE 数据，保全量价数据。")
        # 绝不赋值为 0 以防 Spark 误判，直接传入明确的文本提示
        pe_ttm = "限流暂缺"
    
    # 3. 组装数据包
    payload = {
        "date": trade_date,
        "close": latest_close,
        "ma60": ma60,
        "pe_ttm": pe_ttm
    }
    
    print(f"数据清洗完毕: {payload}")
    
    # 4. 推送到 Google Sheets
    response = requests.post(WEB_APP_URL, json=payload)
    print(f"Google Sheets 响应: {response.text}")

if __name__ == "__main__":
    get_haixing_data()
