import streamlit as st
import requests
import streamlit.components.v1 as components

# ────────────────────────────────
# 設定
MISSKEY_INSTANCE = "seikora.one"
API_TOKEN        = st.secrets["MISSKEY_API_TOKEN"]
API_URL          = f"https://{MISSKEY_INSTANCE}/api/notes/local-timeline"
BATCH_SIZE       = 60
# ────────────────────────────────

st.title("📸 Misskey ローカルTL メディアビューア（seikora.one）")

# セッションステート初期化
if "media_urls" not in st.session_state:
    st.session_state.media_urls = []
    st.session_state.until_id    = None
    st.session_state.has_more    = True

@st.cache_data(ttl=60)
def fetch_batch(token, limit, until_id=None):
    """Misskey ローカルTLをバッチで取得"""
    payload = {"i": token, "limit": limit, "withFiles": True}
    if until_id:
        payload["untilId"] = until_id
    res = requests.post(API_URL, json=payload)
    res.raise_for_status()
    return res.json()

def load_more():
    """次のバッチを読み込んで media_urls に追加"""
    notes = fetch_batch(API_TOKEN, BATCH_SIZE, st.session_state.until_id)
    if not notes:
        st.session_state.has_more = False
        return
    # 次の untilId を設定（最終ノートの ID）
    st.session_state.until_id = notes[-1]["id"]
    # メディア URL を積み増し
    for note in notes:
        for f in note.get("files", []):
            if f["type"].startswith(("image", "video")):
                st.session_state.media_urls.append(f["url"])
    # 取得件数が BATCH_SIZE 未満なら追加読み込みなし
    if len(notes) < BATCH_SIZE:
        st.session_state.has_more = False

# 最初のバッチ読み込み
if not st.session_state.media_urls and st.session_state.has_more:
    load_more()

# 「次の60件を読み込む」ボタン
if st.session_state.has_more:
    if st.button("次の60件を読み込む"):
        load_more()
        # st.experimental_rerun() は不要です。Streamlit が自動で再実行してくれます。

try:
    if st.session_state.media_urls:
        imgs_html = "\n".join(
            f'<img src="{url}" class="media" style="display:none; width:100%; height:auto;">'
            for url in st.session_state.media_urls
        )
        html_code = f"""
        <div id="viewer" style="touch-action: pan-y;">
          {imgs_html}
        </div>
        <script>
          const container = document.getElementById("viewer");
          const imgs = container.querySelectorAll(".media");
          let idx = 0;
          imgs[idx].style.display = "block";
          let startX = 0;
          container.addEventListener("touchstart", e => {{
            startX = e.changedTouches[0].screenX;
          }});
          container.addEventListener("touchend", e => {{
            const diff = e.changedTouches[0].screenX - startX;
            if (Math.abs(diff) > 50) {{
              imgs[idx].style.display = "none";
              idx = (idx + (diff < 0 ? 1 : -1) + imgs.length) % imgs.length;
              imgs[idx].style.display = "block";
            }}
          }});
        </script>
        """
        components.html(html_code, height=500, scrolling=False)
    else:
        st.info("画像または動画を含むノートが見つかりませんでした。")
except Exception as e:
    st.error(f"エラーが発生しました：{e}")