import json
import streamlit as st
import requests
import streamlit.components.v1 as components

# ────────────────────────────────
# 設定
MISSKEY_INSTANCE = "seikora.one"
API_TOKEN        = st.secrets["MISSKEY_API_TOKEN"]
API_URL          = f"https://{MISSKEY_INSTANCE}/api/notes/local-timeline"
BATCH_SIZE       = 60
API_TOKEN = st.secrets["MISSKEY_API_TOKEN"]
API_URL = f"https://{MISSKEY_INSTANCE}/api/notes/local-timeline"
BATCH_SIZE = 60
# ────────────────────────────────

st.title("📸 Misskey ローカルTL メディアビューア（seikora.one）")

# ── セッションステート初期化 ─────────────────
if "media_urls" not in st.session_state:
    st.session_state.media_urls = []
    st.session_state.until_id    = None
    st.session_state.has_more    = True

@st.cache_data(ttl=60)
def fetch_batch(token, limit, until_id=None):
    """ローカルTLをバッチで取得"""
def fetch_batch(token: str, limit: int, until_id: str | None = None):
    """ローカルTLをバッチ取得"""
    payload = {"i": token, "limit": limit, "withFiles": True}
    if until_id:
        payload["untilId"] = until_id
    res = requests.post(API_URL, json=payload)
    res.raise_for_status()
    return res.json()

def load_more():
    """次のバッチを読み込んで media_urls に追加"""
    notes = fetch_batch(API_TOKEN, BATCH_SIZE, st.session_state.until_id)
try:
    notes = fetch_batch(API_TOKEN, BATCH_SIZE)
    if not notes:
        st.session_state.has_more = False
        return
    # until_id を更新（最終ノートのID）
    st.session_state.until_id = notes[-1]["id"]
    # メディアURLを積み増し
    for note in notes:
        for f in note.get("files", []):
            if f["type"].startswith(("image", "video")):
                st.session_state.media_urls.append(f["url"])
    # 取得件数が少なければ読み込み終了
    if len(notes) < BATCH_SIZE:
        st.session_state.has_more = False

# 初回ロード
if not st.session_state.media_urls and st.session_state.has_more:
    load_more()
        st.info("画像または動画を含むノートが見つかりませんでした。")
    else:
        until_id = notes[-1]["id"]
        medias: list[dict[str, str]] = []
        for note in notes:
            for f in note.get("files", []):
                if f["type"].startswith(("image", "video")):
                    medias.append({"url": f["url"], "type": f["type"]})
        init_data = json.dumps({
            "medias": medias,
            "untilId": until_id,
            "token": API_TOKEN,
        })
        html_code = f"""
<div id='viewer' style='touch-action: pan-y;'>
  <div id='content'></div>
</div>
<script>
const API_URL = "{API_URL}";
let data = {init_data};
let medias = data.medias;
let untilId = data.untilId;
const token = data.token;
let idx = 0;
const content = document.getElementById('content');

# ── 「次の60件を読み込む」ボタン ─────────────────
if st.session_state.has_more:
    if st.button("次の60件を読み込む"):
        load_more()
function createEl(m) {{
  let el;
  if (m.type.startsWith('video')) {{
    el = document.createElement('video');
    el.src = m.url;
    el.controls = true;
    el.autoplay = true;
    el.loop = true;
    el.muted = true;
  }} else {{
    el = document.createElement('img');
    el.src = m.url;
  }}
  el.style.width = '100%';
  el.style.height = 'auto';
  return el;
}}

# ── メディア表示 ─────────────────
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
function render() {{
  content.innerHTML = '';
  if (medias[idx]) {{
    content.appendChild(createEl(medias[idx]));
  }}
}}

      container.addEventListener("touchstart", e => {{
        startX = e.changedTouches[0].screenX;
      }});

      container.addEventListener("touchend", e => {{
        const diff = e.changedTouches[0].screenX - startX;
        if (Math.abs(diff) > 50) {{
          imgs[idx].style.display = "none";
          idx = (idx + (diff < 0 ? 1 : -1) + imgs.length) % imgs.length;
          imgs[idx].style.display = "block";
async function fetchMore() {{
  const res = await fetch(API_URL, {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{
      i: token,
      limit: {BATCH_SIZE},
      withFiles: true,
      untilId: untilId
    }})
  }});
  const notes = await res.json();
  if (notes.length > 0) {{
    untilId = notes[notes.length - 1].id;
    for (const note of notes) {{
      const fs = note.files || [];
      for (const f of fs) {{
        if (f.type.startsWith('image') || f.type.startsWith('video')) {{
          medias.push({{url: f.url, type: f.type}});
        }}
      }});
    </script>
    """
    components.html(html_code, height=500, scrolling=False)
      }}
    }}
  }}
}}

render();

else:
    st.info("画像または動画を含むノートが見つかりませんでした。")
const viewer = document.getElementById('viewer');
let startX = 0;
viewer.addEventListener('touchstart', e => {{
  startX = e.changedTouches[0].screenX;
}});
viewer.addEventListener('touchend', async e => {{
  const diff = e.changedTouches[0].screenX - startX;
  if (Math.abs(diff) > 50) {{
    idx += diff < 0 ? 1 : -1;
    if (idx < 0) idx = 0;
    if (idx >= medias.length) {{
      await fetchMore();
    }}
    if (idx >= medias.length) idx = medias.length - 1;
    render();
  }}
}});
</script>
"""
        components.html(html_code, height=500, scrolling=False)
except Exception as e:
    st.error(f"エラーが発生しました：{e}")


