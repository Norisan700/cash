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
st.write("迷わずできる「3ステップ手順」でレジ締めを案内します。")

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

        st.markdown("---")
        st.subheader("💡 迷わずできる！レジ締め3ステップ手順")

        # ステップ1: レジから抜く
        st.markdown("### **ステップ 1：レジから以下のお金をすべて「抜く」**")
        st.write("※これにより、手元に「売上金」と「両替用の元手」がすべて揃います。")
        for d in sorted(remove_list.keys(), reverse=True):
            qty = remove_list[d]
            unit = "札" if d >= 1000 else "玉"
            st.write(f"・**{d}円{unit}** ➡ **{qty} 枚** 抜く")

        # ステップ2: 売上袋に入れる
        st.markdown(f"### **ステップ 2：抜いたお金から、売上回収金「{expected_collect:,} 円」を売上袋に入れる**")
        st.write(f"※お札を中心に、ちょうど **{expected_collect:,} 円分** を売上袋にしまってください。")

        # ステップ3: 残りを金庫で両替してレジに入れる
        st.markdown("### **ステップ 3：手元に残ったお金を金庫へ持っていき、以下に「両替」してレジに入れる**")
        if len(add_list) > 0:
            st.write("※手元に残ったお金（小銭や細かいお札）は、金庫で以下の必要な硬貨に両替してレジに戻します。")
            for d in sorted(add_list.keys(), reverse=True):
                qty = add_list[d]
                unit = "札" if d >= 1000 else "玉"
                st.write(f"・**{d}円{unit}** ➡ **{qty} 枚** レジに入れる")
        else:
            st.success("※両替は不要です！ステップ2まででレジ内は綺麗に5万円になります。")

        # 最終確認用
        with st.expander("調整後のレジ内内訳（合計50,000円）"):
            for denom in DENOMS:
                st.write(f"{denom}円: {optimal_layout[denom]}枚 ({denom * optimal_layout[denom]:,}円)")