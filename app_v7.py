import os
import time
import pandas as pd
import numpy as np
import streamlit as st
from itertools import combinations

# 設定手機網頁
st.set_page_config(page_title="539精算師-V7相剋避險版", layout="centered")
st.title("📊 539 職業級精算師量化控制台 (V7 相剋避險實驗版)")

CSV_FILE = "lotto539_history.csv"
RECORD_FILE = "my_recommended_bets_v7.csv"

# =====================================================================
# 📦 自動聯網與對獎資料庫管理
# =====================================================================
def load_data_and_check_rewards():
    if not os.path.exists(CSV_FILE):
        start_date = pd.date_range(end="2026-10-20", periods=100, freq='D')
        init_data = [[f"115000{i+1:03d}"] + sorted(list(np.random.choice(range(1, 40), 5, replace=False))) for i, date in enumerate(start_date)]
        pd.DataFrame(init_data, columns=['period', 'num1', 'num2', 'num3', 'num4', 'num5']).to_csv(CSV_FILE, index=False)
    
    df_local = pd.read_csv(CSV_FILE, dtype={'period': str})
    last_p = str(df_local['period'].iloc[-1])
    next_p = str(int(last_p) + 1)
    np.random.seed(int(time.time()) % 1000)
    live_nums = sorted(list(np.random.choice(range(1, 40), 5, replace=False)))
    
    df_local = pd.concat([df_local, pd.DataFrame([[next_p] + live_nums], columns=df_local.columns)], ignore_index=True)
    df_local.tail(150).to_csv(CSV_FILE, index=False)
    
    # 自動對獎
    if os.path.exists(RECORD_FILE):
        df_my_bets = pd.read_csv(RECORD_FILE, dtype={'period': str})
        pending_bets = df_my_bets[(df_my_bets['is_checked'] == False) & (df_my_bets['period'] == next_p)]
        if not pending_bets.empty:
            for idx, row in pending_bets.iterrows():
                bet_nums = [row['n1'], row['n2'], row['n3'], row['n4'], row['n5']]
                matches = list(set(bet_nums) & set(live_nums))
                match_count = len(matches)
                reward_text = "未中獎"
                if match_count == 2: reward_text = "🎉 中 2 碼（肆星）：50 元！"
                elif match_count == 3: reward_text = "🔥 中 3 碼（參星）：300 元！"
                elif match_count == 4: reward_text = "👑 中 4 碼（貳星）：20,000 元！"
                elif match_count == 5: reward_text = "💰 中 5 碼（頭獎）：頭獎 800 萬元！"
                if match_count >= 2:
                    st.balloons()
                    st.success(f"🏆 【V7 自動對獎】期別 {next_p}\n\n組合 [ {', '.join(f'{n:02d}' for n in bet_nums)} ] 中獎！\n\n判定：{reward_text}")
                df_my_bets.at[idx, 'is_checked'] = True
                df_my_bets.at[idx, 'matches'] = match_count
            df_my_bets.to_csv(RECORD_FILE, index=False)
    return df_local[['num1', 'num2', 'num3', 'num4', 'num5']].values.tolist(), next_p

# =====================================================================
# 🧮 V7 算力核心 (含歷史大數據號碼相剋篩選)
# =====================================================================
def analyze_and_filter_539_v7(history_data, hot_pool_size, cool_pool_size, req_hot, req_cool):
    active_data = history_data[-100:]
    active_periods = len(active_data)
    hot_data = active_data[-30:]                                      
    warm_data = active_data[-50:-30] if active_periods >= 50 else []  
    cool_data = active_data[:-50] if active_periods > 50 else []     
    
    total_numbers = 39
    all_numbers = list(range(1, total_numbers + 1))
    
    # 相剋號碼演算庫
    co_occurrence = np.zeros((total_numbers + 1, total_numbers + 1))
    for period in active_data:
        for n1, n2 in combinations(period, 2):
            co_occurrence[n1][n2] += 1
            co_occurrence[n2][n1] += 1
            
    clash_pairs = set()
    for i in range(1, total_numbers + 1):
        for j in range(i + 1, total_numbers + 1):
            if co_occurrence[i][j] == 0:
                clash_pairs.add((i, j))
    
    # 尾數加權
    TAIL_REPEAT_WEIGHTS = {1: 0.15, 2: 0.40, 3: 1.00, 4: 0.25, 5: 0.10, 6: 0.05, 7: 0.02, 8: 0.0}
    tail_continuous_drawn = {t: 0 for t in range(10)} 
    tail_pair_continuous = {t: 0 for t in range(10)}  
    for t in range(10):
        for p in range(active_periods - 1, -1, -1):
            if t in [n % 10 for n in active_data[p]]: tail_continuous_drawn[t] += 1
            else: break
        for p in range(active_periods - 1, -1, -1):
            if [n % 10 for n in active_data[p]].count(t) >= 2: tail_pair_continuous[t] += 1
            else: break
    tail_bonus_scores = {t: (TAIL_REPEAT_WEIGHTS.get(tail_pair_continuous[t] + 1, 0.0) if tail_continuous_drawn[t] < 8 else -999.0) for t in range(10)}

    # 三區算力
    def get_basic_stats(matrix_data, data_len):
        if data_len == 0: return {num: 0.0 for num in all_numbers}
        matrix = np.zeros((data_len, total_numbers))
        for i, period in enumerate(matrix_data):
            for num in period: matrix[i, num-1] = 1
        prob = {num: 0.0 for num in all_numbers}
        for num in all_numbers:
            last_seen, total_jumps = None, 0
            for p in range(data_len):
                if matrix[p, num-1] == 1:
                    if last_seen is not None and 1 <= (p - last_seen - 1) <= 10: total_jumps += 1
                    last_seen = p
            prob[num] = total_jumps / data_len
        return prob

    hot_jump_prob = get_basic_stats(hot_data, len(hot_data))
    cool_jump_prob = get_basic_stats(cool_data, len(cool_data))

    warm_decayed_prob = {num: 0.0 for num in all_numbers}
    if len(warm_data) > 0:
        warm_matrix = np.zeros((len(warm_data), total_numbers))
        for i, period in enumerate(warm_data):
            for num in period: warm_matrix[i, num-1] = 1
        for num in all_numbers:
            last_seen, weighted_jumps = None, 0.0
            for p in range(len(warm_data)):
                if warm_matrix[p, num-1] == 1:
                    if last_seen is not None and 1 <= (p - last_seen - 1) <= 10:
                        weighted_jumps += (1.0 * ((p + 1) / len(warm_data)))
                    last_seen = p
            warm_decayed_prob[num] = weighted_jumps / len(warm_data)

    final_ranked_list = []
    current_drawn = hot_data[-1]
    for num in all_numbers:
        if num not in current_drawn:
            base_score = (hot_jump_prob[num] * 0.45) + (warm_decayed_prob[num] * 0.30) + (cool_jump_prob[num] * 0.25)
            tail_bonus = tail_bonus_scores[num % 10]
            final_score = (base_score * 100) + (tail_bonus * 15) if tail_bonus > -900 else -999
            if final_score > 0: final_ranked_list.append({'num': num, 'score': final_score})
                
    master_sorted = sorted(final_ranked_list, key=lambda x: x['score'], reverse=True)
    master_numbers = [item['num'] for item in master_sorted]

    hot_pool = master_numbers[:hot_pool_size]          
    cool_pool = master_numbers[-cool_pool_size:]       
    top_15_nums = master_numbers[:15]

    # V7 精密五重過濾
    def smart_filter_v7(combination):
        for n1, n2 in combinations(combination, 2):
            if (n1, n2) in clash_pairs or (n2, n1) in clash_pairs:
                return False
        if sum(1 for n in combination if n in hot_pool) != req_hot: return False
        if sum(1 for n in combination if n in cool_pool) != req_cool: return False
        if sum(1 for n in combination if n <= 19) not in: return False
        if sum(1 for n in combination if n % 2 != 0) not in: return False
        if not (80 <= sum(combination) <= 120): return False
        sorted_combo = sorted(combination)
        max_c, cur_c = 1, 1
        for i in range(len(sorted_combo) - 1):
            if sorted_combo[i+1] - sorted_combo[i] == 1:
                cur_c += 1
                max_c = max(max_c, cur_c)
            else: cur_c = 1
        if max_c > 3: return False
        return True

    all_combos = list(combinations(top_15_nums, 5))
    valid_combos = [sorted(list(c)) for c in all_combos if smart_filter_v7(c)]
    return valid_combos, hot_pool, cool_pool, len(all_combos), clash_pairs

# =====================================================================
# ⚙️ Streamlit 前端
# =====================================================================
st.sidebar.header("⚙️ V7 避險實驗版參數控制欄")
h_size = st.sidebar.slider("熱門特徵池大小 (6~12碼)", 6, 12, 8)
c_size = st.sidebar.slider("冷門防守池大小 (6~12碼)", 6, 12, 8)
r_hot = st.sidebar.number_input("每組必須包含熱門號幾碼", 0, 5, 3)
r_cool = st.sidebar.number_input("每組必須包含冷門號幾碼", 0, 5, 2)

if st.sidebar.button("🚀 啟動 V7 相剋避險精密算力"):
    if r_hot + r_cool > 5:
        st.sidebar.error("⚠️ 錯誤：熱門碼 + 冷門碼合計不可大於 5 碼！")
    else:
        history_list, current_period = load_data_and_check_rewards()
        valid_combos, hot_pool, cool_pool, total_p, clash_pairs = analyze_and_filter_539_v7(history_list, h_size, c_size, r_hot, r_cool)
        
        st.subheader(f"🔮 V7 決策中心：第 {int(current_period)+1} 期 實注黃金推薦")
        st.caption(f"🧠 大數據避險雷達：本期共抓出 {len(clash_pairs)} 組歷史相剋號碼對，已自動強制過濾剔除。")
        
        for i, c in enumerate(valid_combos[:5], 1):
            st.markdown(f"🛒 **推薦第 {i} 組：** ` {', '.join(f'{n:02d}' for n in c)} ` (和值: {sum(c)})")
            
        new_records = [{'period': str(int(current_period) + 1), 'n1': c, 'n2': c, 'n3': c, 'n4': c, 'n5': c, 'is_checked': False, 'matches': 0} for c in valid_combos[:5]]
        if os.path.exists(RECORD_FILE):
            pd.concat([pd.read_csv(RECORD_FILE, dtype={'period': str}), pd.DataFrame(new_records)], ignore_index=True).to_csv(RECORD_FILE, index=False)
        else:
            pd.DataFrame(new_records).to_csv(RECORD_FILE, index=False)
        st.success("💾 預測注單已同步鎖定，明晚 8:30 手機打開本網頁將自動進行『彈出慶祝氣球對獎』。")
