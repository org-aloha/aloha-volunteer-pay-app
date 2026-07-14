import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# ==========================================
# 1. 設定・定数
# ==========================================
# スプシ①：謝礼対象者の詳細を管理するシート
URL_SHEET_1 = "https://docs.google.com/spreadsheets/d/1WvU83in9itV8pILiHEkITr6eRFRe5EE_xfHsNxRFD3g/edit?usp=sharing"

# スプシ②：全体のまとめログを記録するシート
URL_SHEET_2 = "https://docs.google.com/spreadsheets/d/13_8_vJI7zO7p2MY0VIYKwNRwHgEAm9frd1pdUCDmEXs/edit?usp=sharing"

# ==========================================
# 2. 便利関数
# ==========================================
def get_sheet_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = dict(st.secrets["gcp_json"]) # ← dict() に変更！
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def clear_form():
    st.session_state.reset_counter += 1
    st.session_state.recipient_count = 1
    st.session_state.show_confirm = False
    st.session_state.submission_success = False

# 日付フォーマットの整形
def format_dates(date_input):
    if isinstance(date_input, tuple):
        if len(date_input) == 2:
            return f"{date_input[0].strftime('%Y/%m/%d')} 〜 {date_input[1].strftime('%Y/%m/%d')}"
        elif len(date_input) == 1:
            return date_input[0].strftime('%Y/%m/%d')
        return ""
    return date_input.strftime('%Y/%m/%d') if date_input else ""

# ==========================================
# 3. メイン UI
# ==========================================
st.set_page_config(page_title="ボランティア謝礼申請", layout="centered")
st.title("ボランティア謝礼申請")

# 状態管理（Session State）の初期化
if 'recipient_count' not in st.session_state:
    st.session_state.recipient_count = 1
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0
if 'show_confirm' not in st.session_state:
    st.session_state.show_confirm = False
if 'submission_success' not in st.session_state:
    st.session_state.submission_success = False

# 完了画面の表示
if st.session_state.submission_success:
    st.success("申請が完了し、スプレッドシートに保存されました！")
    st.button("✨ 入力をクリアして新しく申請する", on_click=clear_form, type="primary")
    st.stop() 

# ① 基本情報入力
st.subheader("1. 企画情報")

# 企画区分の選択
project_type = st.selectbox(
    "企画区分",
    ["対面mtg", "キャンパスツアー当日", "サマーキャンプ当日", "東京修学旅行当日", "その他"],
    key=f"p_type_{st.session_state.reset_counter}"
)

# 企画区分の選択に応じた追加項目
project_name = ""
if project_type == "対面mtg":
    project_name = st.text_input("企画名", key=f"p_name_{st.session_state.reset_counter}")
elif project_type == "その他":
    project_name = st.text_input("企画名（内容）", key=f"p_name_{st.session_state.reset_counter}")

# スプシに書き込むための「企画名＋企画区分」文字列
combined_project = f"{project_name}{project_type}" if project_name else project_type

# 日時入力
dates = st.date_input(
    "日時 (期間の場合は開始日と終了日を選択)",
    value=[], 
    key=f"dates_{st.session_state.reset_counter}"
)

st.divider()

# ② 謝礼対象者入力
st.subheader("2. 謝礼対象者（スタッフ）")
recipients_data = []

# 日数入力が必要な区分の定義
needs_days = project_type in ["サマーキャンプ当日", "東京修学旅行当日"]

for i in range(st.session_state.recipient_count):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        r_name = st.text_input(f"対象者名 {i+1}", key=f"r_name_{st.session_state.reset_counter}_{i}")
    
    days = 1
    days_str = ""
    with col2:
        if needs_days:
            # 半角数字（整数）の入力
            days = st.number_input(f"参加日数", min_value=1, step=1, key=f"r_days_{st.session_state.reset_counter}_{i}")
            days_str = str(days)
    
    if r_name.strip():
        # 金額と計算式の作成
        if project_type == "対面mtg":
            unit_price = 800
        else:
            unit_price = 1000
            
        reward = unit_price * days
        
        # 12列目用の文字列: "日数(ある場合)×単位あたりの金額=合計金額"
        if needs_days:
            calc_str = f"{days}日×{unit_price}円={reward}円"
        else:
            # 参加日数入力がない区分（1日扱い）の場合
            calc_str = f"1日×{unit_price}円={reward}円"
            
        recipients_data.append({
            "name": r_name.strip(),
            "days_str": days_str,
            "reward": reward,
            "calc_str": calc_str  # ← これを追加
        })

if st.button("＋ 対象者を追加"):
    st.session_state.recipient_count += 1
    st.rerun()

st.divider()

# ③ 送信＆確認フロー
if not st.session_state.show_confirm:
    if st.button("完了", type="primary"):
        # 入力チェック
        if (project_type in ["対面mtg", "その他"]) and not project_name.strip():
            st.error(f"「{project_type}」が選択されています。企画名を入力してください。")
        elif not dates:
            st.error("日時を入力してください。")
        elif not recipients_data:
            st.error("少なくとも1名の対象者を入力してください。")
        else:
            st.session_state.show_confirm = True
            st.rerun()
else:
    st.warning("⚠️ 執行部メンバーは謝礼対象者に含まれません。このまま完了してもよろしいでしょうか。")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("OK (申請を確定する)", type="primary"):
            with st.spinner("スプレッドシートに保存中..."):
                try:
                    client = get_sheet_client()
                    now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                    date_str = format_dates(dates)
                    
                    # --- [スプシ①] 詳細データの書き込み ---
                    sheet_1 = client.open_by_url(URL_SHEET_1).get_worksheet(0)
                    rows_for_sheet_1 = []
                    for r in recipients_data:
                        # A列: 企画名+企画区分, B列: 日時, C列: 対象者名, D列: 参加日数(無い場合は空白), E列: 報酬額
                        rows_for_sheet_1.append([
                            combined_project, 
                            date_str, 
                            r["name"], 
                            r["days_str"], 
                            r["reward"]
                        ])
                    
                    #append_rows でまとめて一括追記（上書き・消去を防ぎます）
                    sheet_1.append_rows(rows_for_sheet_1)

                    # --- [スプシ②] まとめログの書き込み ---
                    sheet_2 = client.open_by_url(URL_SHEET_2).get_worksheet(0)
                    rows_for_sheet_2 = []
                    for r in recipients_data:
                        # 対象者ごとに1行（13列分の空リストを作成）
                        row2 = [""] * 13
                        row2[0] = now_str                           # 1列目: タイムスタンプ
                        row2[2] = r["name"]                         # 3列目: スタッフ名(対象者名)
                        row2[3] = f"{combined_project}謝礼"          # 4列目: 企画名+区分+謝礼
                        row2[11] = r["calc_str"]                    # 12列目: 計算式
                        row2[12] = r["reward"]                      # 13列目: 報酬額
                        rows_for_sheet_2.append(row2)
                        
                    # スプシ②も append_rows で一括追記
                    sheet_2.append_rows(rows_for_sheet_2)

                    st.balloons()
                    st.session_state.show_confirm = False
                    st.session_state.submission_success = True
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
                    
    with col2:
        if st.button("キャンセルして修正する"):
            st.session_state.show_confirm = False
            st.rerun()