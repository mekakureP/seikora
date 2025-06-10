import streamlit as st
import requests
import streamlit.components.v1 as components

MISSKEY_INSTANCE = "seikora.one"
API_TOKEN = st.secrets["MISSKEY_API_TOKEN"]
API_URL = f"https://{MISSKEY_INSTANCE}/api/notes/local-timeline"

st.title("📺 フルスクリーン＆スワイプ対応 Misskey メディアビューア")

@st.cache_data(ttl=60)
def fetch_local_timeline(token, limit=30):
    res = requests.post(API_URL, json={"i": token, "limit": limit, "withFiles": True})
    res.raise_for_status()
    return res.json()

try:
    notes = fetch_local_timeline(API_TOKEN)
    media_urls = [
        f["url"]
        for note in notes
        for f in note.get("files", [])
        if f["type"].startswith(("image", "video"))
    ]

    if media_urls:
        # HTML/JS を組み立て
        imgs_html = "\n".join(
            f'<img src="{url}" class="media" style="display:none; max-width:100%; max-height:100%;">'
            for url in media_urls
        )
        html_code = f"""
        <style>
          body {{ margin:0; overflow:hidden; }} 
          #viewer {{ position:fixed; top:0; left:0; width:100vw; height:100vh; background:#000; touch-action: pan-y; display:flex; align-items:center; justify-content:center; }}
          .media {{ object-fit:contain; }}
          #fs-btn {{ position:fixed; bottom:20px; right:20px; z-index:999; padding:10px 15px; background:rgba(255,255,255,0.7); border:none; border-radius:5px; font-size:16px; }}
        </style>
        <div id="viewer">
          {imgs_html}
          <button id="fs-btn">⛶</button>
        </div>
        <script>
          const container = document.getElementById("viewer");
          const btnFS = document.getElementById("fs-btn");
          const medias = container.querySelectorAll(".media");
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
          btnFS.addEventListener("click", () => {{
            if (!document.fullscreenElement) {{
              container.requestFullscreen().catch(err => console.error(err));
            }} else {{
              document.exitFullscreen().catch(err => console.error(err));
            }}
          }});
        </script>
        """
        components.html(html_code, height=600, scrolling=False)

    else:
        st.info("ローカルTLにメディアファイルが見つかりませんでした。")

except Exception as e:
    st.error(f"エラーが発生しました：{e}")


