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

st.set_page_config(page_title="Misskey メディアビューア", layout="wide")
st.title("📺 フルスクリーン＆スワイプ＆ページング対応 Misskey メディアビューア")

# セッションステート初期化
if "media_urls" not in st.session_state:
    st.session_state.media_urls = []
    st.session_state.until_id    = None
    st.session_state.has_more    = True

@st.cache_data(ttl=60)
def fetch_batch(token: str, limit: int, until_id: str | None = None):
    """Misskey ローカルTLをバッチで取得"""
    payload = {"i": token, "limit": limit, "withFiles": True}
    if until_id:
        payload["untilId"] = until_id
    res = requests.post(API_URL, json=payload)
    res.raise_for_status()
    return res.json()

def load_more():
    """次のバッチを読み込んで media_urls に追加（リノート除外）"""
    notes = fetch_batch(API_TOKEN, BATCH_SIZE, st.session_state.until_id)
    if not notes:
        st.session_state.has_more = False
        return
    st.session_state.until_id = notes[-1]["id"]
    for note in notes:
        if note.get("renote") is not None:
            continue
        for f in note.get("files", []):
            if f["type"].startswith(("image", "video")):
                st.session_state.media_urls.append(f["url"])
    if len(notes) < BATCH_SIZE:
        st.session_state.has_more = False

# 最初のバッチ読み込み
if not st.session_state.media_urls and st.session_state.has_more:
    load_more()

# 「次の60件を読み込む」ボタン
if st.session_state.has_more:
    if st.button("次の60件を読み込む"):
        load_more()
        st.experimental_rerun()

if not st.session_state.media_urls:
    st.info("ローカルTLに画像・動画を含むノートが見つかりませんでした。")
else:
    # HTML/JS ビューワーの組み立て
    imgs_html = "\n".join(
        # .gif は <img> タグでアニメ表示
        f'<img src="{url}" class="media" style="display:none;">'
        if url.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
        else f'<video src="{url}" class="media" style="display:none;" controls autoplay loop muted></video>'
        for url in st.session_state.media_urls
    )

    html_code = f"""
    <style>
      /* 全画面黒背景コンテナ */
      #viewer {{
        position: fixed; top: 0; left: 0;
        width: 100vw; height: 100vh;
        background: #000;
        display: flex; align-items: center; justify-content: center;
        touch-action: pan-y; overflow: hidden; margin: 0; padding: 0;
      }}
      /* メディアを画面にフィット */
      .media {{
        max-width: 100%; max-height: 100%; object-fit: contain;
      }}
      /* フルスクリーン切替ボタン */
      #fs-btn {{
        position: fixed; bottom: 20px; right: 20px;
        z-index: 999; padding: 10px 15px;
        background: rgba(255,255,255,0.7); border: none;
        border-radius: 5px; font-size: 16px; cursor: pointer;
      }}
    </style>
    <div id="viewer">
      {imgs_html}
      <button id="fs-btn">⛶</button>
    </div>
    <script>
      const container = document.getElementById("viewer");
      const medias = Array.from(container.querySelectorAll(".media"));
      let idx = 0;
      medias[idx].style.display = "block";

      // スワイプ検知
      let startX = 0;
      container.addEventListener("touchstart", e => {{ startX = e.changedTouches[0].screenX; }});
      container.addEventListener("touchend", e => {{
        const diff = e.changedTouches[0].screenX - startX;
        if (Math.abs(diff) > 50) {{
          medias[idx].style.display = "none";
          idx = (idx + (diff < 0 ? 1 : -1) + medias.length) % medias.length;
          medias[idx].style.display = "block";
        }}
      }});

      // フルスクリーン切替
      document.getElementById("fs-btn").addEventListener("click", () => {{
        if (!document.fullscreenElement) {{
          container.requestFullscreen();
        }} else {{
          document.exitFullscreen();
        }}
      }});
    </script>
    """

    # コンポーネント埋め込み
    components.html(html_code, height=800, scrolling=False)




