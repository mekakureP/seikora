import streamlit as st
import requests
import json
import streamlit.components.v1 as components

# ────────────────────────────────
# 設定
MISSKEY_INSTANCE = "seikora.one"
API_TOKEN        = st.secrets["MISSKEY_API_TOKEN"]
API_URL          = f"https://{MISSKEY_INSTANCE}/api/notes/local-timeline"
BATCH_SIZE       = 60
# ────────────────────────────────

st.title("📸 Misskey ローカルTL メディアビューア（自動バッチ＆スワイプ）")

@st.cache_data(ttl=60)
def fetch_initial(token: str, limit: int, until_id: str | None = None):
    """Misskey ローカルTLをバッチ取得"""
    payload = {"i": token, "limit": limit, "withFiles": True}
    if until_id:
        payload["untilId"] = until_id
    res = requests.post(API_URL, json=payload)
    res.raise_for_status()
    return res.json()

# Python 側で最初の 60 件を取得
initial_notes = fetch_initial(API_TOKEN, BATCH_SIZE)
initial_media = [
    {"url": f["url"], "type": f["type"]}
    for note in initial_notes
    for f in note.get("files", [])
    if f["type"].startswith(("image", "video"))
]
# 次バッチ取得用 until_id
initial_until_id = initial_notes[-1]["id"] if initial_notes else None

# JSON にエンコードして JS へ渡す準備\media_json = json.dumps(initial_media)
until_id_js = "null" if initial_until_id is None else f'"{initial_until_id}"'

# HTML + JavaScript
html_code = f"""
<div id="viewer" style="
    position: fixed; top:0; left:0;
    width:100vw; height:100vh;
    background:#000;
    display:flex; align-items:center; justify-content:center;
    overflow:hidden; touch-action: pan-y;
"></div>

<script>
const apiUrl    = "{API_URL}";
const token     = "{API_TOKEN}";
const batchSize = {BATCH_SIZE};
let untilId     = {until_id_js};
let medias      = {media_json};

const container = document.getElementById("viewer");
let idx = 0;

// メディア要素作成ヘルパー
function makeElement(item) {{
  if (item.type.startsWith("video")) {{
    const v = document.createElement("video");
    v.src      = item.url;
    v.controls = true;
    v.autoplay = true;
    v.loop     = true;
    v.muted    = true;
    v.style.maxWidth  = "100%";
    v.style.maxHeight = "100%";
    v.style.objectFit = "contain";
    v.style.display   = "none";
    return v;
  }} else {{
    const img = document.createElement("img");
    img.src             = item.url;
    img.style.maxWidth  = "100%";
    img.style.maxHeight = "100%";
    img.style.objectFit = "contain";
    img.style.display   = "none";
    return img;
  }}
}}

// 全メディアを renderer
function renderAll() {{
  container.innerHTML = "";
  medias.forEach(item => {{
    container.appendChild(makeElement(item));
  }});
}}

// 現在のインデックスを表示
function showIdx() {{
  Array.from(container.children).forEach((el, i) => {{
    el.style.display = (i === idx ? "block" : "none");
  }});
}}

// 次バッチ読み込み
async function loadMore() {{
  const payload = {{ i: token, limit: batchSize }};
  if (untilId) payload.untilId = untilId;
  const res = await fetch(apiUrl, {{
    method: "POST",
    headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify(payload)
  }});
  const notes = await res.json();
  if (!notes.length) return;
  untilId = notes[notes.length - 1].id;
  notes.forEach(note => {{
    note.files.forEach(f => {{
      if (f.type.startsWith("image") || f.type.startsWith("video")) {{
        medias.push({{ url: f.url, type: f.type }});
      }}
    }});
  }});
  renderAll();  // 追加後も idx を保持
}}

// 初期描画
renderAll();
showIdx();

// タッチスワイプ検知
let startX = 0;
container.addEventListener("touchstart", e => {{ startX = e.changedTouches[0].screenX; }});
container.addEventListener("touchend", async e => {{
  const diff = e.changedTouches[0].screenX - startX;
  if (Math.abs(diff) > 50) {{
    idx = (idx + (diff < 0 ? 1 : -1) + medias.length) % medias.length;
    showIdx();
    if (idx === medias.length - 1) await loadMore();
  }}
}});
</script>
"""

components.html(html_code, height=800, scrolling=False)


