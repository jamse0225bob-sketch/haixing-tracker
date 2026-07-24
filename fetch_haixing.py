import os
import requests
import pandas as pd
import datetime
import tushare as ts

# ================= 核心配置区 =================
# 你已授权且验证存活的有效 Google Sheets 接收接口
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxyPTllOdzZhqFVG-I263Zzi8Pt_VQPRFshIUMC_aop_rVXayG08BYAOvPYmU9JZhyR/exec"
SYMBOL = "603556.SH"

def get_haixing_data():
    # 鉴权阻断机制
    tushare_token = os.environ.get("TUSHARE_TOKEN")
    if not tushare_token:
        raise ValueError("致命错误：未找到 TUSHARE_TOKEN 环境变量。请检查 GitHub Secrets 配置。")
    
    ts.set_token(tushare_token)
    pro = ts.pro_api()
    
    # 提取当前服务器的自然日
    today_str = datetime.datetime.now().strftime('%Y%m%d')
    print(f"[{datetime.datetime.now()}] 开始通过 Tushare 提取标的 {SYMBOL} 行情...")
    
    # ================= 阶段 1：获取绝对量价锚点 =================
    # limit=60 保证即便是周末或长假，也能抓取到最近的一个真实交易日及前期均线
    df_daily = pro.daily(ts_code=SYMBOL, end_date=today_str, limit=60)
    
    if df_daily.empty:
        raise ValueError("系统熔断：未能抓取到任何历史交易数据，请检查 Tushare 接口额度或标的代码。")

    latest_close = float(df_daily['close'].iloc[0]) # 索引 0 永远是最近一个交易日
    ma60 = round(float(df_daily['close'].mean()), 2)
    
    # 【修复隐患】：剥离出实际发生交易的真实日期（例如周五），以此为锚点去查询配套估值
    actual_trade_date = str(df_daily['trade_date'].iloc[0])
    
    # ================= 阶段 2：估值装甲降级机制 =================
    try:
        # 使用真实的 actual_trade_date 进行精准打击，规避周末查无数据的问题
        df_basic = pro.daily_basic(ts_code=SYMBOL, trade_date=actual_trade_date, fields='ts_code,trade_date,pe_ttm')
        if not df_basic.empty:
            pe_ttm = round(float(df_basic['pe_ttm'].iloc[0]), 2)
        else:
            pe_ttm = "估值未生成"
    except Exception as e:
        print(f"警告: 估值接口受限 ({e})。启动非对称降级，舍弃 PE，保全量价生命线。")
        pe_ttm = "限流暂缺"
    
    # ================= 阶段 3：数据清洗与组装 (新增偏离度补丁) =================
    # 计算当前收盘价偏离 60日均线的百分比，保留两位小数
    deviation = round(((latest_close - ma60) / ma60) * 100, 2)
    
    payload = {
        "date": actual_trade_date,
        "close": latest_close,
        "ma60": ma60,
        "pe_ttm": pe_ttm,
        "deviation": deviation  # 传给表格的新增字段
    }
    print(f"数据清洗完毕: {payload}")
    
    # ================= 阶段 4：强校验弹道投递 =================
    # 加入溯源探针，暴露真实的投递地址
    print(f"正在向此地址发送数据: [{WEB_APP_URL}]")
    
    # 强制声明 JSON 报文格式，防止 Google 接收端静默丢弃
    headers = {'Content-Type': 'application/json'}
    
    response = requests.post(WEB_APP_URL, json=payload, headers=headers)
    print(f"Google Sheets 响应状态码: {response.status_code}")
    print(f"Google Sheets 响应正文: {response.text}")

if __name__ == "__main__":
    get_haixing_data()
