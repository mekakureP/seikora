import streamlit as st
import requests
import os

# Misskey から初期バッチを取得
API_TOKEN = os.getenv("MISSKEY_API_TOKEN") or st.secrets["MISSKEY_API_TOKEN"]
def fetch_batch(limit=60, until_id=None):
    payload = {"i": API_TOKEN, "limit": limit, "withFiles": True}
    if until_id: payload["untilId"] = until_id
    r = requests.post(f"https://seikora.one/api/notes/local-timeline", json=payload)
    r.raise_for_status()
    return r.json()

notes = fetch_batch()
# medias: {'url', 'type', 'text'}
medias = []
for note in notes:
    txt = note.get("text") or note.get("renote",{}).get("text","")
    snippet = "\n".join(txt.splitlines()[:3])
    for f in note.get("files",[]):
        if f["type"].startswith(("image","video")):
            medias.append({"url":f["url"], "type":f["type"], "text":snippet})
    
# セッションステートで現在のインデックス管理
if "idx" not in st.session_state:
    st.session_state.idx = 0

# ナビゲーション
col1, col2 = st.columns(2)
if col1.button("← 前へ") and st.session_state.idx > 0:
    st.session_state.idx -= 1
if col2.button("次へ →") and st.session_state.idx < len(medias)-1:
    st.session_state.idx += 1

# 表示
item = medias[st.session_state.idx]
st.write(f"**{st.session_state.idx+1}/{len(medias)}**")
if item["type"].startswith("video"):
    st.video(item["url"])
else:
    st.image(item["url"], use_column_width=True)
st.markdown("---")
st.text(item["text"])
