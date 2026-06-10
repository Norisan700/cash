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

def solve_exchange_and_sales(current_counts, optimal_layout, expected_collect):
    """
    レジから取り除くお金(removed_pool)を、
    1. 金庫との両替用の元手 (exchange_out)
    2. 売上回収袋に入れるお金 (sales_bag)
    にきれいに分離する。
    """
    # 差分の整理
    diff = {}
    for d in DENOMS:
        diff[d] = current_counts.get(d, 0) - optimal_layout[d]
    # 10000円は全額回収対象
    diff[10000] = current_counts.get(10000, 0)
    
    removed_pool = []  # レジから減らす金種 (denom, qty)
    added_pool = []    # レジに足す金種 (denom, qty)
    
    for d, qty in diff.items():
        if qty > 0:
            removed_pool.append((d, qty))
        elif qty < 0:
            added_pool.append((d, abs(qty)))
            
    # 金庫から貰う必要のある総額
    total_added_value = sum(d * qty for d, qty in added_pool)
    
    # 金庫に渡す用の組み合わせ（小さい金種を優先的に両替の元手にするために昇順ソート）
    pool_sorted = sorted(removed_pool, key=lambda x: x[0])
    
    exchange_out = {}
    
    def search_exchange(idx, target, current_sol):
        if target == 0:
            return current_sol.copy()
        if idx == len(pool_sorted):
            return None
        
        denom, max_qty = pool_sorted[idx]
        limit = min(max_qty, target // denom)
        for qty in range(limit, -1, -1):
            if qty > 0:
                current_sol[denom] = qty
            else:
                if denom in current_sol:
                    del current_sol[denom]
            res = search_exchange(idx + 1, target - denom * qty, current_sol)
            if res is not None:
                return res
        return None

    # 等価両替ができる組み合わせを探索
    exchange_sol = search_exchange(0, total_added_value, {})
    
    if exchange_sol is not None:
        # 売上袋に入れる分を計算 (全体から両替用を引いたもの)
        sales_bag = {}
        for d, qty in removed_pool:
            qty_for_exchange = exchange_sol.get(d, 0)
            qty_for_sales = qty - qty_for_exchange
            if qty_for_sales > 0:
                sales_bag[d] = qty_for_sales
        return exchange_sol, added_pool, sales_bag
    else:
        # ぴったり両替が成立しない場合はNone（フォールバック用）
        return None, added_pool, None

# --- Web画面の構築 ---
st.set_page_config(page_title="レジ締めサポートツール", layout="centered")
st.title("🪙 レジ締め・両替サポート")
st.write("売上回収袋に入れるお金と、金庫と両替するお金を完全に分離して提案します。")

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
        # 分離アルゴリズムの実行
        exchange_sol, added_pool, sales_bag = solve_exchange_and_sales(current_counts, optimal_layout, expected_collect)
        
        # 1. 売上回収袋に入れるアクション
        st.subheader("🛍️ 【売上袋】に入れるもの（合計: " + f"{expected_collect:,}円）")
        st.write("※これらはそのまま売上回収用の袋にしまってください。")
        if sales_bag:
            for d in sorted(sales_bag.keys(), reverse=True):
                qty = sales_bag[d]
                unit = "札" if d >= 1000 else "玉"
                st.write(f"・**{d}円{unit}** ➡ **{qty} 枚** を売上袋へ")
        else:
            # 万が一きれいに分離できなかった場合のセーフガード
            st.write("・レジ内の全額から50,000円を差し引いた額を回収してください。")

        # 2. 金庫との両替アクション
        st.subheader("🔄 【金庫】と両替するもの")
        st.write("※レジ内の金種バランスを整えるための『等価両替』です。損得はありません。")
        
        if exchange_sol and len(added_pool) > 0:
            col_ex1, col_ex2 = st.columns(2)
            with col_ex1:
                st.markdown("**👉 金庫へ持って行くもの（渡す）**")
                for d, qty in sorted(exchange_sol.items(), reverse=True):
                    unit = "札" if d >= 1000 else "玉"
                    st.write(f"・{d}円{unit}: **{qty} 枚**")
            with col_ex2:
                st.markdown("**👈 金庫から持って来るもの（貰う）**")
                for d, qty in sorted(added_pool, key=lambda x: x[0], reverse=True):
                    unit = "札" if d >= 1000 else "玉"
                    st.write(f"・{d}円{unit}: **{qty} 枚**")
        elif len(added_pool) == 0:
            st.success("素晴らしい！金庫との両替は不要です。売上を抜くだけで綺麗に5万円になります。")
        else:
            st.warning("金庫との等価両替プランが自動計算できませんでした。レジ内の硬貨が不足しているため、手動で両替を行ってください。")

        # 最終確認用
        with st.expander("調整後のレジ内内訳（合計50,000円）"):
            for denom in DENOMS:
                st.write(f"{denom}円: {optimal_layout[denom]}枚 ({denom * optimal_layout[denom]:,}円)")