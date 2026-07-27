import os
import requests
import pandas as pd
import datetime
import tushare as ts
import yfinance as yf

# ================= 核心配置区 =================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxyPTllOdzZhqFVG-I263Zzi8Pt_VQPRFshIUMC_aop_rVXayG08BYAOvPYmU9JZhyR/exec"
SYMBOL = "603556.SH"

def calculate_rsi(data, periods=14):
    """精确计算 RSI (相对强弱指数)"""
    delta = data.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=periods-1, adjust=False).mean()
    ema_down = down.ewm(com=periods-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

def get_haixing_data():
    tushare_token = os.environ.get("TUSHARE_TOKEN")
    if not tushare_token:
        raise ValueError("未找到 TUSHARE_TOKEN")
    ts.set_token(tushare_token)
    pro = ts.pro_api()
    today_str = datetime.datetime.now().strftime('%Y%m%d')
    
    print(f"[{datetime.datetime.now()}] 开始量化特征提取...")
    
    # === 1. 量价指标提取 (MA60, MA20, RSI) ===
    # 提取过去 100 个交易日以保证 RSI 和均线计算的平滑度
    df_daily = pro.daily(ts_code=SYMBOL, end_date=today_str, limit=100)
    if df_daily.empty:
        raise ValueError("系统熔断：未抓取到交易数据。")
        
    df_daily = df_daily.sort_values('trade_date', ascending=True).reset_index(drop=True)
    
    latest_close = float(df_daily['close'].iloc[-1])
    actual_trade_date = str(df_daily['trade_date'].iloc[-1])
    
    # 计算 MA60 和 MA20
    ma60 = round(float(df_daily['close'].tail(60).mean()), 2)
    ma20 = round(float(df_daily['close'].tail(20).mean()), 2)
    
    # 计算均线偏离度
    ma60_deviation = round(((latest_close - ma60) / ma60) * 100, 2)
    ma20_deviation = round(((latest_close - ma20) / ma20) * 100, 2)
    
    # 计算 RSI-14
    df_daily['rsi'] = calculate_rsi(df_daily['close'])
    rsi_14 = round(float(df_daily['rsi'].iloc[-1]), 2)
    
    # === 2. 基本面防线：估值与业绩 ===
    try:
        df_basic = pro.daily_basic(ts_code=SYMBOL, trade_date=actual_trade_date, fields='pe_ttm')
        pe_ttm = round(float(df_basic['pe_ttm'].iloc[0]), 2) if not df_basic.empty else "估值未生成"
    except Exception:
        pe_ttm = "限流暂缺"
        
    # 获取最新的财务指标：dt_netprofit_yoy (扣非净利润同比增速)
    # 直接赋值，剥离一切网络请求与异常捕获
    net_profit_yoy = "参考表格手工维护"

    # === 3. 宏观防线：汇率波动 ===
    # 利用 yfinance 获取 USD/CNY (美元兑人民币) 近一个月的走势
    try:
        fx_data = yf.download('USDCNY=X', period='1mo', progress=False)
        if not fx_data.empty:
            fx_start = float(fx_data['Close'].iloc[0])
            fx_end = float(fx_data['Close'].iloc[-1])
            # 计算美元相对人民币的涨跌幅（正数代表美元升值/人民币贬值，利好出海）
            usdcny_change = round(((fx_end - fx_start) / fx_start) * 100, 2)
        else:
            usdcny_change = "获取失败"
    except Exception as e:
        usdcny_change = "接口受限"

    # === 4. 组装超限战 payload ===
    payload = {
        "date": actual_trade_date,
        "close": latest_close,
        "ma60": ma60,
        "pe_ttm": pe_ttm,
        "ma60_deviation": ma60_deviation,
        "ma20_deviation": ma20_deviation,
        "rsi_14": rsi_14,
        "net_profit_yoy": net_profit_yoy,
        "usdcny_change": usdcny_change
    }
    
    print(f"底层特征清洗完毕: {payload}")
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post(WEB_APP_URL, json=payload, headers=headers)
    print(f"Google Sheets 响应状态码: {response.status_code}")

if __name__ == "__main__":
    get_haixing_data()
