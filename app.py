import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# ==========================================
# 1. 設定・定数
# ==========================================
# スプシ①：謝礼対象者の詳細を管理するシート
URL_SHEET_1 = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_1_ID/edit"

# スプシ②：企画単位の全体ログ（サマリー）を記録するシート
URL_SHEET_2 = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_2_ID/edit"

# ==========================================
# 2. 便利関数
# ==========================================
def get_sheet_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = json.loads(st.secrets["gcp_json"])
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
    st.stop() # 以降のUIは描画しない

# ① 基本情報入力
st.subheader("1. 企画情報")
project_name = st.text_input("企画名", key=f"project_name_{st.session_state.reset_counter}")

# 日時（単日〜複数日対応）
dates = st.date_input(
    "日時 (期間の場合は開始日と終了日を選択してください)",
    value=[], 
    key=f"dates_{st.session_state.reset_counter}"
)

st.divider()

# ② 謝礼対象者入力
st.subheader("2. 謝礼対象者")
recipients_list = []

for i in range(st.session_state.recipient_count):
    r_name = st.text_input(f"対象者名 {i+1}", key=f"r_name_{st.session_state.reset_counter}_{i}")
    if r_name.strip():
        recipients_list.append(r_name.strip())

if st.button("＋ 対象者を追加"):
    st.session_state.recipient_count += 1
    st.rerun()

st.divider()

# ③ 送信＆確認フロー
if not st.session_state.show_confirm:
    # 最初の「完了」ボタン
    if st.button("完了", type="primary"):
        if not project_name:
            st.error("企画名を入力してください。")
        elif not dates:
            st.error("日時を入力してください。")
        elif not recipients_list:
            st.error("少なくとも1名の謝礼対象者を入力してください。")
        else:
            # 入力チェックOKなら確認画面を表示するフラグを立てる
            st.session_state.show_confirm = True
            st.rerun()
else:
    # 確認画面
    st.warning("⚠️ 執行部メンバーは謝礼対象者に含まれません。このまま完了してもよろしいでしょうか。")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("OK (申請を確定する)", type="primary"):
            with st.spinner("スプレッドシートに保存中..."):
                try:
                    client = get_sheet_client()
                    now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                    date_str = format_dates(dates)
                    
                    # --- [スプシ①への書き込み] 謝礼対象者ごとの詳細データ ---
                    sheet_detail = client.open_by_url(URL_SHEET_1).get_worksheet(0)
                    detail_rows = []
                    for recipient in recipients_list:
                        # 例: [タイムスタンプ, 企画名, 日時, 対象者名]
                        detail_rows.append([now_str, project_name, date_str, recipient])
                    
                    # 対象者の数だけ行を追加
                    for row in detail_rows:
                        sheet_detail.append_row(row)

                    # --- [スプシ②への書き込み] 企画単位のサマリーデータ ---
                    sheet_summary = client.open_by_url(URL_SHEET_2).get_worksheet(0)
                    # 例: [タイムスタンプ, 企画名, 日時, 対象者合計人数]
                    summary_row = [now_str, project_name, date_str, f"{len(recipients_list)}名"]
                    sheet_summary.append_row(summary_row)

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