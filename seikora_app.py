import streamlit as st
import requests
import json
import streamlit.components.v1 as components

# ────────────────────────────────
# Misskey インスタンス設定
MISSKEY_INSTANCE = "seikora.one"
API_TOKEN        = st.secrets["MISSKEY_API_TOKEN"]
LOCAL_API_URL    = f"https://{MISSKEY_INSTANCE}/api/notes/local-timeline"
USER_API_URL     = f"https://{MISSKEY_INSTANCE}/api/users/notes"
BATCH_SIZE       = 60
# ────────────────────────────────

st.title("📸 Misskey メディアビューア（ユーザー指定＆自動バッチ＆スワイプ）")

# ユーザー指定入力（@以下のユーザー名）
raw_user = st.text_input("表示するユーザー名を指定 (例: @username)", value="")
username = raw_user.lstrip("@")

@st.cache_data(ttl=60)
def fetch_batch(token: str, limit: int, until_id: str | None = None):
    """ローカルTLをバッチ取得"""
    payload = {"i": token, "limit": limit, "withFiles": True}
    if until_id:
        payload["untilId"] = until_id
    res = requests.post(LOCAL_API_URL, json=payload)
    res.raise_for_status()
    return res.json()

@st.cache_data(ttl=60)
def fetch_user_notes(token: str, username: str, limit: int, until_id: str | None = None):
    """ユーザーのノート（リノート含む）をバッチ取得"""
    payload = {
        "i": token,
        "username": username,
        "limit": limit,
        "includeMyRenotes": True,
        "withFiles": True
    }
    if until_id:
        payload["untilId"] = until_id
    res = requests.post(USER_API_URL, json=payload)
    res.raise_for_status()
    return res.json()

# 初回バッチ取得
if username:
    notes = fetch_user_notes(API_TOKEN, username, BATCH_SIZE)
    api_url_js = USER_API_URL
else:
    notes = fetch_batch(API_TOKEN, BATCH_SIZE)
    api_url_js = LOCAL_API_URL

# メディア抽出と次バッチ用ID
initial_media = []
for note in notes:
    for f in note.get("files", []):
        if f.get("type", "").startswith(("image", "video")):
            initial_media.append({
                "url": f["url"],
                "type": f["type"],
            })
initial_until_id = notes[-1].get("id") if notes else None

# JSON にエンコード
media_json   = json.dumps(initial_media)
until_id_js  = "null" if initial_until_id is None else f'"{initial_until_id}"'

# 埋め込み HTML + JavaScript
html_code = """
<div id=\"viewer\" style=\"
    position: fixed; top:0; left:0;
    width:100vw; height:100vh;
    background:#000;
    display:flex; align-items:center; justify-content:center;
    overflow:hidden; touch-action: pan-y;
\"></div>
<script>
const apiUrl    = "{api_url}";
const token     = "{token}";
const batchSize = {batch_size};
let untilId     = {until_id};
let medias      = {media_list};
const container = document.getElementById("viewer");
let idx = 0;

function makeElement(item) {{
  if (item.type.startsWith("video")) {{
    const v = document.createElement("video");
    v.src        = item.url;
    v.controls   = true;
    v.autoplay   = true;
    v.loop       = true;
    v.muted      = true;
    v.playsInline= true;
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

function renderAll() {{
  container.innerHTML = "";
  medias.forEach(item => {{ container.appendChild(makeElement(item)); }});
}}

function showIdx() {{
  const children = container.children;
  for (let i = 0; i < children.length; i++) {{
    children[i].style.display = i === idx ? "block" : "none";
  }}
}}

async function loadMore() {{
  const payload = {{ i: token, limit: batchSize }};
  if (untilId) payload.untilId = untilId;
  const res = await fetch(apiUrl, {{
    method: "POST",
    headers: {{"Content-Type":"application/json"}},
    body: JSON.stringify(payload)
  }});
  const notes = await res.json();
  if (!notes.length) return;
  untilId = notes[notes.length - 1].id;
  notes.forEach(note => {{
    note.files.forEach(f => {{
      if (f.type.startsWith("image") || f.type.startsWith("video")) {{
        medias.push({{url: f.url, type: f.type}});
      }}
    }});
  }});
  renderAll();
}}

// 初期描画
renderAll(); showIdx();
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
""".format(
    api_url=api_url_js,
    token=API_TOKEN,
    batch_size=BATCH_SIZE,
    until_id=until_id_js,
    media_list=media_json
)

components.html(html_code, height=800, scrolling=False)


