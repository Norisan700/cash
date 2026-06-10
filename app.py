import streamlit as st

# レジ内に残すべき金種と、その基準範囲
DENOMS = [5000, 1000, 500, 100, 50, 10, 5, 1]
RANGES = {
    5000: (3, 4),      # 3〜4枚
    1000: (20, 30),    # 20〜30枚
    500: (10, 20),     # 10〜20枚
    100: (25, 35),     # 30枚程度
    50: (10, 20),      # 10〜20枚
    10: (25, 35),      # 30枚程度
    5: (10, 20),       # 10〜20枚
    1: (25, 35)        # 30枚程度
}

# 枝刈り用の事前計算
min_rem = []
max_rem = []
for i in range(len(DENOMS)):
    min_rem.append(sum(DENOMS[j] * RANGES[DENOMS[j]][0] for j in range(i, len(DENOMS))))
    max_rem.append(sum(DENOMS[j] * RANGES[DENOMS[j]][1] for j in range(i, len(DENOMS))))
min_rem.append(0)
max_rem.append(0)

def find_optimal_layout(current_counts):
    best_sol = None
    best_cost = float('inf')
    
    def dfs(idx, current_sum, path):
        nonlocal best_sol, best_cost
        if idx == len(DENOMS):
            if current_sum == 50000:
                cost = sum(abs(path[i] - current_counts.get(DENOMS[i], 0)) for i in range(len(DENOMS)))
                if cost < best_cost:
                    best_cost = cost
                    best_sol = path.copy()
            return
        
        denom = DENOMS[idx]
        low, high = RANGES[denom]
        
        for qty in range(low, high + 1):
            next_sum = current_sum + denom * qty
            if next_sum + min_rem[idx+1] > 50000:
                continue
            if next_sum + max_rem[idx+1] < 50000:
                continue
            
            path.append(qty)
            dfs(idx + 1, next_sum, path)
            path.pop()
            
    dfs(0, 0, [])
    if best_sol:
        return {DENOMS[i]: best_sol[i] for i in range(len(DENOMS))}
    return None

# --- Web画面の構築 ---
st.set_page_config(page_title="レジ締めサポートツール", layout="centered")
st.title("🪙 レジ締め・両替サポート")
st.write("「閉店30分前の両替」と「閉店後の回収」のタイムラインに沿って案内します。")

# 入力セクション
st.header("1. 現在のレジ内の状況入力")
col1, col2 = st.columns(2)

current_counts = {}
with col1:
    st.subheader("紙幣")
    current_counts[10000] = st.number_input("10000円札 (枚)", min_value=0, step=1, value=0)
    current_counts[5000] = st.number_input("5000円札 (枚)", min_value=0, step=1, value=0)
    current_counts[1000] = st.number_input("1000円札 (枚)", min_value=0, step=1, value=0)

with col2:
    st.subheader("硬貨")
    current_counts[500] = st.number_input("500円玉 (枚)", min_value=0, step=1, value=0)
    current_counts[100] = st.number_input("100円玉 (枚)", min_value=0, step=1, value=0)
    current_counts[50] = st.number_input("50円玉 (枚)", min_value=0, step=1, value=0)
    current_counts[10] = st.number_input("10円玉 (枚)", min_value=0, step=1, value=0)
    current_counts[5] = st.number_input("5円玉 (枚)", min_value=0, step=1, value=0)
    current_counts[1] = st.number_input("1円玉 (枚)", min_value=0, step=1, value=0)

st.header("2. 本日の現金売上入力")
sales_amount = st.number_input("本日の現金売上金 (円)", min_value=0, step=1, value=0)

# 計算実行
if st.button("最適な両替プランを計算する", type="primary"):
    total_cash_now = sum(k * v for k, v in current_counts.items())
    expected_collect = total_cash_now - 50000
    discrepancy = expected_collect - sales_amount

    st.header("計算結果")
    
    # 指標の表示
    m1, m2, m3 = st.columns(3)
    m1.metric("現在のレジ内総額", f"{total_cash_now:,} 円")
    m2.metric("売上回収に回す額", f"{expected_collect:,} 円")
    m3.metric("レジ過不足", f"{discrepancy:,} 円", delta=discrepancy, delta_color="inverse")

    # 最適な配置を計算
    optimal_layout = find_optimal_layout(current_counts)
    
    if optimal_layout is None:
        st.error("エラー: 現在のレジ内の金額では、つり銭準備金を5万円（基準枚数内）に調整できません。両替用の小銭を金庫から補充してください。")
    else:
        # 差分の計算
        diff = {}
        for d in DENOMS:
            diff[d] = current_counts.get(d, 0) - optimal_layout[d]
        diff[10000] = current_counts.get(10000, 0)
        
        remove_list = {d: qty for d, qty in diff.items() if qty > 0}
        add_list = {d: abs(qty) for d, qty in diff.items() if qty < 0}

        # 30分前の「等価両替用の元手」を計算
        # 小さい金種から優先して両替の支払いにあてる（Greedy法）
        sorted_rem = sorted(remove_list.items(), key=lambda x: x[0])
        v_add = sum(d * qty for d, qty in add_list.items())
        
        vault_handover = {}
        current_handover_value = 0
        
        for d, qty_avail in sorted_rem:
            if current_handover_value >= v_add:
                break
            needed_val = v_add - current_handover_value
            qty_needed = (needed_val + d - 1) // d  # 切り上げ
            qty_to_take = min(qty_avail, qty_needed)
            
            if qty_to_take > 0:
                vault_handover[d] = qty_to_take
                current_handover_value += d * qty_to_take

        # 金庫から戻ってくる「お釣り」の計算
        change_from_vault = current_handover_value - v_add

        # 閉店後にレジから抜く残りの売上金リスト
        final_remove_list = {}
        for d, qty in remove_list.items():
            qty_left = qty - vault_handover.get(d, 0)
            if qty_left > 0:
                final_remove_list[d] = qty_left

        st.markdown("---")
        
        # ===================================================
        # フェーズ1：閉店30分前（両替作業）
        # ===================================================
        st.subheader("⏰ Step 1：閉店30分前（両替・レジの準備）")
        st.write("※営業中に、あらかじめレジの小銭バランスを整えておく作業です。")
        
        if len(add_list) > 0:
            col_ex1, col_ex2 = st.columns(2)
            with col_ex1:
                st.markdown("**👉 金庫へ持って行くもの（渡す）**")
                st.write(f"（合計：**{current_handover_value:,} 円**）")
                for d, qty in sorted(vault_handover.items(), reverse=True):
                    unit = "札" if d >= 1000 else "玉"
                    st.write(f"・{d}円{unit}: **{qty} 枚**")
            with col_ex2:
                st.markdown("**👈 金庫から受け取るもの（貰う）**")
                st.write("**【レジに入れる小銭】**")
                for d, qty in sorted(add_list.items(), reverse=True):
                    unit = "札" if d >= 1000 else "玉"
                    st.write(f"・{d}円{unit}: **{qty} 枚**")
                
                if change_from_vault > 0:
                    st.write("**【お釣り（閉店後用にキープ）】**")
                    st.write(f"・お釣りとして **{change_from_vault:,} 円分** の小銭を受け取る")

            st.markdown("**💡 30分前のアクション指示**")
            st.write("1. 金庫から貰った**【レジに入れる小銭】**をすべてレジに戻します。")
            if change_from_vault > 0:
                st.write(f"2. 金庫から貰ったお釣り（**{change_from_vault:,}円**）は、レジ横のカップ等に入れて**閉店後まで保管**しておきます。")
        else:
            st.success("※このレジは小銭が十分に足りています！30分前の両替作業は不要です。")

        st.markdown("---")

        # ===================================================
        # フェーズ2：閉店後（売上金回収・締め作業）
        # ===================================================
        st.subheader("🏁 Step 2：閉店後（売上回収・最終締め）")
        st.write("※営業終了後、今日の売上金を袋にしまって完了させる作業です。")
        
        st.markdown("**👉 レジから抜くもの**")
        for d in sorted(final_remove_list.keys(), reverse=True):
            qty = final_remove_list[d]
            unit = "札" if d >= 1000 else "玉"
            st.write(f"・**{d}円{unit}** ➡ **{qty} 枚** 抜く")

        st.markdown(f"**🛍️ 売上袋にしまう最終確認（合計: {expected_collect:,} 円）**")
        if change_from_vault > 0:
            st.write(f"・今レジから抜いたお金と、30分前にキープしておいた**お釣り（{change_from_vault:,}円）**を合流させます。")
            st.write(f"　➡ 合計がぴったり **{expected_collect:,} 円** になっていることを確認して売上袋にしまいます。")
        else:
            st.write(f"・今レジから抜いたお金（計 **{expected_collect:,} 円**）をそのまま売上袋にしまいます。")
            
        st.success("これでレジ内はぴったり50,000円（翌日用の基準枚数）になりました。お疲れ様でした！")

        # 最終確認用
        with st.expander("調整後のレジ内内訳（合計50,000円）"):
            for denom in DENOMS:
                st.write(f"{denom}円: {optimal_layout[denom]}枚 ({denom * optimal_layout[denom]:,}円)")