import os
import time
import pandas as pd
import numpy as np
import streamlit as st
from itertools import combinations

# 設定手機網頁標題與暗黑高質感主題
st.set_page_config(page_title="539精算師行動控制台", layout="centered")
st.title("📊 539 職業級精算師行動量化控制台")

CSV_FILE = "lotto539_history.csv"
RECORD_FILE = "my_recommended_bets.csv" # 儲存手機歷史推薦牌組的檔案

# =====================================================================
# 📦 第一部分：自動聯網增量更新與對獎資料庫
# =====================================================================
def load_data_and_check_rewards():
    # 初始化歷史彩券資料
    if not os.path.exists(CSV_FILE):
        start_date = pd.date_range(end="2026-10-20", periods=100, freq='D')
        init_data = [[f"115000{i+1:03d}"] + sorted(list(np.random.choice(range(1, 40), 5, replace=False))) for i, date in enumerate(start_date)]
        pd.DataFrame(init_data, columns=['period', 'num1', 'num2', 'num3', 'num4', 'num5']).to_csv(CSV_FILE, index=False)
    
    df_local = pd.read_csv(CSV_FILE, dtype={'period': str})
    
    # 模擬當晚聯網爬蟲抓到的最新開獎（增量追加）
    last_p = str(df_local['period'].iloc[-1])
    next_p = str(int(last_p) + 1)
    np.random.seed(int(time.time()) % 1000)
    live_nums = sorted(list(np.random.choice(range(1, 40), 5, replace=False)))
    
    # 模擬開獎更新
    df_local = pd.concat([df_local, pd.DataFrame([[next_p] + live_nums], columns=df_local.columns)], ignore_index=True)
    df_local.tail(150).to_csv(CSV_FILE, index=False)
    
    # 🚨 核心：自動歷史對獎邏輯
    if os.path.exists(RECORD_FILE):
        df_my_bets = pd.read_csv(RECORD_FILE, dtype={'period': str})
        # 找出尚未對獎，但官方已經開出獎號的期數
        pending_bets = df_my_bets[(df_my_bets['is_checked'] == False) & (df_my_bets['period'] == next_p)]
        
        if not pending_bets.empty:
            st.toast("🔔 偵測到最新開獎，系統正在為您自動對獎...", icon="🔍")
            for idx, row in pending_bets.iterrows():
                bet_nums = [row['n1'], row['n2'], row['n3'], row['n4'], row['n5']]
                # 計算交集（中了幾碼）
                matches = list(set(bet_nums) & set(live_nums))
                match_count = len(matches)
                
                # 計算 539 獎金分配
                reward_text = "沒中獎，再接再厲"
                if match_count == 2: reward_text = "🎉 中 2 碼（肆星）：獎金 50 元！"
                elif match_count == 3: reward_text = "🔥 中 3 碼（參星）：獎金 300 元！"
                elif match_count == 4: reward_text = "👑 中 4 碼（貳星）：獎金 20,000 元！"
                elif match_count == 5: reward_text = "💰 中 5 碼（頭獎）：榮登頭獎主（800萬元）！"
                
                if match_count >= 2:
                    st.balloons() # 手機螢幕噴出慶祝氣球
                    st.success(f"🏆 【自動對獎通知】期別 {next_p}\n\n您的推薦組合 [ {', '.join(f'{n:02d}' for n in bet_nums)} ] 對中獎號 [ {', '.join(f'{n:02d}' for n in matches)} ]！\n\n判定結果：{reward_text}")
                
                # 更新狀態為已對獎
                df_my_bets.at[idx, 'is_checked'] = True
                df_my_bets.at[idx, 'matches'] = match_count
            df_my_bets.to_csv(RECORD_FILE, index=False)

    return df_local[['num1', 'num2', 'num3', 'num4', 'num5']].values.tolist(), next_p

# =====================================================================
# ⚙️ 第二部分：精算控制台手機配置端
# =====================================================================
st.sidebar.header("⚙️ 精算師權重參數控制欄")
h_size = st.sidebar.slider("熱門特徵池大小 (6~12碼)", 6, 12, 8)
c_size = st.sidebar.slider("冷門防守池大小 (6~12碼)", 6, 12, 8)
r_hot = st.sidebar.number_input("每組必須包含熱門號幾碼", 0, 5, 3)
r_cool = st.sidebar.number_input("每組必須包含冷門號幾碼", 0, 5, 2)

if st.sidebar.button("🚀 啟動行動大腦交叉精算"):
    if r_hot + r_cool > 5:
        st.sidebar.error("⚠️ 錯誤：熱門碼 + 冷門碼合計不可大於 5 碼！")
    else:
        history_list, current_period = load_data_and_check_rewards()
        
        # [此處串接先前的核心 V6 算力邏輯，篩選出最優五組 valid_combos]
        # 模擬產出今日最優 5 組牌 (僅作示範展示，實務上跑 V6 邏輯)
        np.random.seed(42)
        valid_combos = [sorted(list(np.random.choice(range(1, 40), 5, replace=False))) for _ in range(5)]
        
        # 🚨 將今日為您推薦的這 5 組注單寫入「歷史對獎待查檔案」中
        new_records = []
        for combo in valid_combos:
            new_records.append({
                'period': str(int(current_period) + 1), # 鎖定為明晚要開獎的下一期
                'n1': combo[0], 'n2': combo[1], 'n3': combo[2], 'n4': combo[3], 'n5': combo[4],
                'is_checked': False, 'matches': 0
            })
        
        df_new_bets = pd.DataFrame(new_records)
        if os.path.exists(RECORD_FILE):
            df_existing = pd.read_csv(RECORD_FILE, dtype={'period': str})
            df_new_bets = pd.concat([df_existing, df_new_bets], ignore_index=True)
        df_new_bets.to_csv(RECORD_FILE, index=False)
        
        # 輸出今日預測戰報
        st.subheader(f"🎯 明日第 {int(current_period)+1} 期 實注黃金五組推薦")
        for i, c in enumerate(valid_combos, 1):
            st.markdown(f"🛒 **推薦第 {i} 組：** ` {', '.join(f'{n:02d}' for n in c)} `")
        st.info("💡 系統已自動將上述 5 組注單鎖定備忘，明晚 8:30 官方開獎時，手機打開此網頁將會觸發『自動對獎喜報廣播』。")
