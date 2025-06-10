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

st.title("📸 Misskey ローカルTL メディアビューア（インフィニットスワイプ）")

@st.cache_data(ttl=60)
def fetch_batch(token, limit, until_id=None):
    payload = {"i": token, "limit": limit, "withFiles": True}
    if until_id:
        payload["untilId"] = until_id
    res = requests.post(API_URL, json=payload)
    res.raise_for_status()
    return res.json()

# 最初の60件を取得
initial_notes = fetch_batch(API_TOKEN, BATCH_SIZE)
initial_media = []
for note in initial_notes:
    for f in note.get("files", []):
        if f["type"].startswith(("image", "video")):
            initial_media.append({"url": f["url"], "type": f["type"]})
# 次バッチ取得用 ID
initial_until_id = initial_notes[-1]["id"] if initial_notes else None

# HTML/JS で全バッチをクライアントサイドで取得・スワイプ
html_code = f"""
<div id="viewer" style="
    position: fixed; top:0; left:0;
    width:100vw; height:100vh;
    background:#000;
    display:flex; align-items:center; justify-content:center;
    overflow:hidden; touch-action: pan-y;
">
</div>

<script>
const apiUrl   = "{API_URL}";
const token    = "{API_TOKEN}";
const batchSize= {BATCH_SIZE};
let untilId    = "{initial_until_id}";
let medias     = {json.dumps(initial_media)};

const container = document.getElementById("viewer");
let idx = 0;

// メディア要素を作って返す
function makeElement(item) {{
  if (item.type.startsWith("video")) {{
    const v = document.createElement("video");
    v.src = item.url;
    v.controls = true;
    v.autoplay = true;
    v.loop = true;
    v.muted = true;
    v.style.maxWidth = "100%";
    v.style.maxHeight = "100%";
    v.style.objectFit = "contain";
    v.style.display = "none";
    return v;
  }} else {{
    const img = document.createElement("img");
    img.src = item.url;
    img.style.maxWidth = "100%";
    img.style.maxHeight = "100%";
    img.style.objectFit = "contain";
    img.style.display = "none";
    return img;
  }}
}}

// viewer に全メディア要素を追加
function renderAll() {{
  container.innerHTML = "";
  medias.forEach(item => {{
    const el = makeElement(item);
    container.appendChild(el);
  }});
}}

// 現在の idx を表示
function showIdx() {{
  const children = container.children;
  for (let i = 0; i < children.length; i++) {{
    children[i].style.display = i === idx ? "block" : "none";
  }}
}}

// 次バッチを取得して medias に追加
async function loadMore() {{
  const payload = {{ i: token, limit: batchSize }};
  if (untilId) payload.untilId = untilId;
  const res = await fetch(apiUrl, {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify(payload)
  }});
  const notes = await res.json();
  if (notes.length === 0) return;  // もう無ければ終了
  untilId = notes[notes.length - 1].id;
  notes.forEach(note => {{
    note.files.forEach(f => {{
      if (f.type.startsWith("image") || f.type.startsWith("video")) {{
        medias.push({{ url: f.url, type: f.type }});
      }}
    }});
  }});
  renderAll();
}}

// 初期描画
renderAll();
showIdx();

// タッチスワイプ検知
let startX = 0;
container.addEventListener("touchstart", e => {{
  startX = e.changedTouches[0].screenX;
}});
container.addEventListener("touchend", async e => {{
  const diff = e.changedTouches[0].screenX - startX;
  if (Math.abs(diff) > 50) {{
    const prevIdx = idx;
    idx = (idx + (diff < 0 ? 1 : -1) + medias.length) % medias.length;
    showIdx();
    // 最後の要素に到達したら次バッチ読込
    if (idx === medias.length - 1) {{
      await loadMore();
    }}
  }}
}});
</script>
"""

components.html(html_code, height=800, scrolling=False)
