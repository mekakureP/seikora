import streamlit as st
import requests
import json
import streamlit.components.v1 as components
import os

# ────────────────────────────────
# Misskey インスタンス設定
MISSKEY_INSTANCE = "seikora.one"
LOCAL_API_URL    = f"https://{MISSKEY_INSTANCE}/api/notes/local-timeline"
USER_API_URL     = f"https://{MISSKEY_INSTANCE}/api/users/notes"
SHOW_USER_URL    = f"https://{MISSKEY_INSTANCE}/api/users/show"
BATCH_SIZE       = 60
# ────────────────────────────────

st.title("📸 Misskey メディアビューア")

# ── API トークン取得（環境変数 → st.secrets → 手入力）─────────────────
API_TOKEN = os.getenv("MISSKEY_API_TOKEN") or st.secrets.get("MISSKEY_API_TOKEN")
if not API_TOKEN:
    API_TOKEN = st.text_input("Misskey API トークンを入力してください", type="password")
    if not API_TOKEN:
        st.warning("API トークンが設定されていません。入力が必要です。")
        st.stop()

# ── 取得モード選択 ─────────────────────────
mode = st.radio("取得モードを選択", ("ローカルTL", "ユーザー指定TL"), index=0)
username = None
if mode == "ユーザー指定TL":
    raw_user = st.text_input("表示するユーザー名を指定（@以下）", value="")
    username = raw_user.lstrip("@") or None

# ── API 呼び出し関数定義 ─────────────────────────
@st.cache_data(ttl=60)
def fetch_batch(token: str, limit: int, until_id: str | None = None):
    payload = {"i": token, "limit": limit, "withFiles": True}
    if until_id:
        payload["untilId"] = until_id
    res = requests.post(LOCAL_API_URL, json=payload)
    res.raise_for_status()
    return res.json()

@st.cache_data(ttl=300)
def fetch_user_id(token: str, username: str) -> str:
    res = requests.post(SHOW_USER_URL, json={"i": token, "username": username})
    res.raise_for_status()
    return res.json().get("id")

@st.cache_data(ttl=60)
def fetch_user_notes(token: str, user_id: str, limit: int, until_id: str | None = None):
    payload = {"i": token, "userId": user_id, "limit": limit, "includeMyRenotes": True, "withFiles": True}
    if until_id:
        payload["untilId"] = until_id
    res = requests.post(USER_API_URL, json=payload)
    res.raise_for_status()
    return res.json()

# ── 初回ノート取得 ─────────────────────────
if mode == "ユーザー指定TL" and username:
    user_id = fetch_user_id(API_TOKEN, username)
    notes = fetch_user_notes(API_TOKEN, user_id, BATCH_SIZE)
    api_url = USER_API_URL
else:
    notes = fetch_batch(API_TOKEN, BATCH_SIZE)
    api_url = LOCAL_API_URL

# ── メディアリスト生成（name フィールド追加） ─────────────────────────
initial_media = []
for note in notes:
    for f in note.get("files", []):
        if f.get("type", "").startswith(("image", "video")):
            initial_media.append({"url": f["url"], "name": f.get("name", ""), "type": f["type"]})
    ren = note.get("renote")
    if ren:
        for f in ren.get("files", []):
            if f.get("type", "").startswith(("image", "video")):
                initial_media.append({"url": f["url"], "name": f.get("name", ""), "type": f["type"]})
initial_until_id = notes[-1].get("id") if notes else None

# ── HTML/JS ビューア埋め込み ─────────────────────────
html_code = '''
<div id="viewer" style="position:fixed;top:0;left:0;width:100vw;height:100vh;background:#000;display:flex;align-items:center;justify-content:center;overflow:hidden;touch-action:pan-y;"></div>
<script>
const apiUrl    = "{api_url}";
const token     = "{api_token}";
const batchSize = {batch_size};
let untilId     = {until_id};
let medias      = {media_list};
const container = document.getElementById("viewer");
let idx = 0;

function makeElement(item) {{
  if (item.type.startsWith("video")) {{
    const wrapper = document.createElement("div");
    wrapper.style.display = "flex";
    wrapper.style.flexDirection = "column";
    wrapper.style.alignItems = "center";

    const v = document.createElement("video");
    v.src            = item.url;
    v.controls       = true;
    v.autoplay       = true;
    v.loop           = true;
    v.muted          = true;
    v.playsInline    = true;
    v.setAttribute("playsinline", "");
    v.setAttribute("x-webkit-playsinline", "");
    v.crossOrigin    = "anonymous";
    v.style.maxWidth  = "100%";
    v.style.maxHeight = "100%";
    v.style.objectFit = "contain";
    wrapper.appendChild(v);

    const link = document.createElement("a");
    link.href         = item.url;
    link.textContent  = item.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.style.color  = "#fff";
    link.style.marginTop = "8px";
    wrapper.appendChild(link);

    return wrapper;
  }} else {{
    const img = document.createElement("img");
    img.src            = item.url;
    img.style.maxWidth  = "100%";
    img.style.maxHeight = "100%";
    img.style.objectFit = "contain";
    return img;
  }}
}}

function renderAll() {{ container.innerHTML = ""; medias.forEach(item => container.appendChild(makeElement(item))); }}
function showIdx() {{ Array.from(container.children).forEach((el,i) => el.style.display = i===idx?"block":"none"); }}

async function loadMore() {{
  const payload = {{ i: token, limit: batchSize }};
  if (untilId) payload.untilId = untilId;
  const res = await fetch(apiUrl, {{ method:"POST", headers:{{"Content-Type":"application/json"}}, body:JSON.stringify(payload) }});
  const notes = await res.json(); if (!notes.length) return;
  untilId = notes[notes.length-1].id;
  notes.forEach(note => {{
    note.files.forEach(f => {{ if(f.type.startsWith("image")||f.type.startsWith("video")) medias.push({{url:f.url,name:f.name,type:f.type}}); }});
    if(note.renote) note.renote.files.forEach(f => {{ if(f.type.startsWith("image")||f.type.startsWith("video")) medias.push({{url:f.url,name:f.name,type:f.type}}); }});
  }});
  renderAll();
}}

// 初期描画
renderAll(); showIdx(); let startX=0;
container.addEventListener("touchstart", e => {{ startX = e.changedTouches[0].screenX; }});
container.addEventListener("touchend", async e => {{
  const diff = e.changedTouches[0].screenX - startX;
  if (Math.abs(diff) > 50) {{ idx = (idx + (diff < 0 ? 1 : -1) + medias.length) % medias.length; showIdx(); if (idx === medias.length - 1) await loadMore(); }}
}});

// ダブルタップ操作
container.addEventListener("dblclick", e => {{
  const x = e.clientX;
  const w = window.innerWidth;
  const children = container.children;
  children[idx].style.display = "none";
  if (x < w / 2) {{ idx = (idx - 1 + children.length) % children.length; }} else {{ idx = (idx + 1) % children.length; }}
  children[idx].style.display = "block";
}});
</script>
'''.format(
    api_url=api_url,
    api_token=API_TOKEN,
    batch_size=BATCH_SIZE,
    until_id=json.dumps(initial_until_id),
    media_list=json.dumps(initial_media)
)

components.html(
    html_code,
    height=800,
    scrolling=False,
    key="media_viewer",
    unsafe_allow_html=True
)




