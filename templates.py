"""内置默认工作流与图片卡片 HTML 模板。

这些内容只是数据，与绘图逻辑分开存放，方便单独修改卡片样式。
"""

# 内置的 SD1.5 文生图示例工作流（API 格式）。
# 当用户没有在配置里填写「默认工作流」时使用这一份。
# 占位符全部用引号包裹，保证它本身就是合法 JSON。
DEFAULT_WORKFLOW = """{
  "3": {
    "class_type": "KSampler",
    "inputs": {
      "seed": "%seed%",
      "steps": "%steps%",
      "cfg": "%cfg%",
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1,
      "model": ["4", 0],
      "positive": ["6", 0],
      "negative": ["7", 0],
      "latent_image": ["5", 0]
    }
  },
  "4": {
    "class_type": "CheckpointLoaderSimple",
    "inputs": { "ckpt_name": "v1-5-pruned-emaonly.safetensors" }
  },
  "5": {
    "class_type": "EmptyLatentImage",
    "inputs": { "width": "%width%", "height": "%height%", "batch_size": "%batch_size%" }
  },
  "6": {
    "class_type": "CLIPTextEncode",
    "inputs": { "text": "%prompt%", "clip": ["4", 1] }
  },
  "7": {
    "class_type": "CLIPTextEncode",
    "inputs": { "text": "%negative_prompt%", "clip": ["4", 1] }
  },
  "8": {
    "class_type": "VAEDecode",
    "inputs": { "samples": ["3", 0], "vae": ["4", 2] }
  },
  "9": {
    "class_type": "SaveImage",
    "inputs": { "filename_prefix": "AstrBot", "images": ["8", 0] }
  }
}"""


DRAW_HELP_TMPL = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width={{ (820 * (scale | default(2))) | int }}, height=10"/>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { font-family: "PingFang SC","Microsoft YaHei","Hiragino Sans GB","Noto Sans CJK SC",sans-serif; background: #eef0fb; }
  .card {
    width: 820px; zoom: {{ scale | default(2) }}; position: relative; overflow: hidden; color: #5a6890;
    background:
      radial-gradient(circle at 12% 8%, rgba(246,198,168,0.4), transparent 24%),
      radial-gradient(circle at 88% 10%, rgba(168,224,194,0.4), transparent 26%),
      radial-gradient(circle at 8% 88%, rgba(243,182,203,0.38), transparent 26%),
      radial-gradient(circle at 90% 90%, rgba(156,195,239,0.42), transparent 28%),
      linear-gradient(162deg, #eaedfb 0%, #eef0fb 38%, #f3edfa 74%, #e9edfb 100%);
  }
  .hd { position: relative; display: flex; justify-content: space-between; align-items: center; padding: 28px 32px 8px 32px; }
  .hd-l { display: flex; align-items: center; gap: 13px; }
  .logo { font-size: 38px; }
  .title { font-size: 29px; font-weight: 800; color: #6b7bc4; }
  .subtitle { font-size: 14px; color: #8b96c8; margin-top: 4px; }
  .emblem { border: 2px solid #cbb28c; border-radius: 13px; padding: 6px 15px; text-align: center; background: rgba(255,255,255,0.5); }
  .emblem-i { font-size: 18px; line-height: 1; }
  .emblem-t { font-size: 12px; font-weight: 800; letter-spacing: 2px; color: #a98a5f; line-height: 1.25; margin-top: 2px; }
  .deco { position: absolute; opacity: 0.32; pointer-events: none; }
  .body { position: relative; z-index: 1; padding: 12px 24px 6px 24px; }
  .group {
    background: #ffffff; border-radius: 18px; padding: 16px 22px; margin-bottom: 14px;
    box-shadow: 0 6px 22px rgba(150,160,210,0.16);
  }
  .group-h { font-size: 16.5px; font-weight: 800; color: #6b7bc4; padding-bottom: 8px; margin-bottom: 8px; border-bottom: 1.5px dashed #e6e9f6; }
  .cmd { display: flex; align-items: baseline; gap: 12px; padding: 6px 2px; }
  .cmd + .cmd { border-top: 1px solid #f1f3fb; }
  .cmd-name { flex-shrink: 0; min-width: 190px; font-weight: 700; font-size: 14.5px; color: #5b78c4; }
  .cmd-desc { flex: 1; font-size: 13px; line-height: 1.5; color: #6a76a0; }
  .cmd-tag { flex-shrink: 0; font-size: 10.5px; font-weight: 700; padding: 1px 7px; border-radius: 7px;
             background: #fce8ef; color: #d97a9a; align-self: center; }
  .pgrid { display: flex; flex-wrap: wrap; gap: 8px 18px; }
  .pi { width: 47%; display: flex; align-items: baseline; gap: 9px; padding: 4px 0; }
  .pn { flex-shrink: 0; font-family: Consolas, Menlo, monospace; font-size: 12.5px; font-weight: 700;
        background: #eaf1fc; color: #5f80b6; padding: 2px 8px; border-radius: 8px; }
  .pd { font-size: 12.5px; color: #6a76a0; }
  .ex { background: #f4f6fd; border-radius: 12px; padding: 11px 15px; }
  .ex-l { font-family: Consolas, Menlo, monospace; font-size: 13px; color: #5a6890; line-height: 2; }
  .info { text-align: center; font-size: 12.5px; color: #8b96c8; margin: 6px 0 2px 0; line-height: 1.8; }
  .footer { position: relative; z-index: 1; text-align: center; padding: 14px; margin-top: 6px;
            color: #9aa6c2; font-size: 12.5px; border-top: 1px solid rgba(200,205,235,0.5); }
</style>
</head>
<body>
<div class="card">
  <span class="deco" style="top:20px;left:290px;font-size:17px;">&#127912;</span>
  <span class="deco" style="top:70px;right:200px;font-size:14px;">&#10024;</span>
  <span class="deco" style="bottom:64px;left:28px;font-size:15px;">&#128396;&#65039;</span>
  <span class="deco" style="bottom:110px;right:26px;font-size:16px;">&#127800;</span>

  <div class="hd">
    <div class="hd-l">
      <div class="logo">&#127912;</div>
      <div>
        <div class="title">智乃的画室 · 绘图帮助</div>
        <div class="subtitle">想画点什么？这些都交给智乃吧～</div>
      </div>
    </div>
    <div class="emblem">
      <div class="emblem-i">&#128396;&#65039;</div>
      <div class="emblem-t">CHINO'S<br/>ATELIER</div>
    </div>
  </div>

  <div class="body">
    {% for g in groups %}
    <div class="group">
      <div class="group-h">{{ g.title }}</div>
      {% for c in g['items'] %}
      <div class="cmd"><span class="cmd-name">{{ c.cmd }}</span><span class="cmd-desc">{{ c.desc }}</span>{% if c.admin %}<span class="cmd-tag">管理员</span>{% endif %}</div>
      {% endfor %}
    </div>
    {% endfor %}

    <div class="group">
      <div class="group-h">&#127899;&#65039; 可选参数（跟在提示词后，均可省略）</div>
      <div class="pgrid">
        {% for p in params %}<div class="pi"><span class="pn">{{ p.name }}</span><span class="pd">{{ p.desc }}</span></div>{% endfor %}
      </div>
    </div>

    <div class="group">
      <div class="group-h">&#128221; 示例</div>
      <div class="ex">{% for e in examples %}<div class="ex-l">{{ e }}</div>{% endfor %}</div>
    </div>

    <div class="info">{{ wf_line }}<br/>{{ mode_line }}</div>
  </div>

  <div class="footer">&#128048; Rabbit House ｜ 今天也画点温柔的东西吧。</div>
</div>
</body>
</html>
"""

# 博丽灵梦风格的 /云绘图预设 卡片。
# 数据：reimu_items / items = [{name, icon, desc, size, thumb（可选 data URI）}], illust（可选 data URI）, scale
CLOUD_PRESET_CARD_TMPL = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width={{ (760 * (scale | default(2))) | int }}, height=10"/>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    font-family: "PingFang SC","Microsoft YaHei","Hiragino Sans GB","Noto Sans CJK SC",sans-serif;
    background: #fbefee;
  }
  .serif { font-family: "Noto Serif CJK SC","Source Han Serif SC","Songti SC","SimSun",serif; }
  .card {
    width: 760px; zoom: {{ scale | default(2) }}; position: relative; overflow: hidden; color: #4d3336;
    background:
      radial-gradient(circle at 92% 60%, rgba(214,48,64,0.06), transparent 26%),
      linear-gradient(180deg, #fffaf8 0%, #fdf3f1 60%, #fbecea 100%);
  }
  .banner {
    position: relative; min-height: 108px; padding: 22px 26px 24px 26px; color: #fffaf6;
    background: linear-gradient(170deg, #df3646 0%, #c8283a 65%, #b11f31 100%);
    display: flex; align-items: center; gap: 14px;
  }
  .banner.has-illust { padding-right: 160px; }
  .orb { flex-shrink: 0; filter: drop-shadow(0 3px 4px rgba(90,10,20,0.35)); }
  .title { font-size: 26px; font-weight: 900; letter-spacing: 2px; text-shadow: 0 2px 0 rgba(100,10,20,0.35); }
  .subtitle { font-size: 13px; color: #ffe1dc; margin-top: 5px; letter-spacing: 1px; }
  .illust {
    position: absolute; right: 14px; bottom: -36px; width: 140px; height: 140px; z-index: 3;
    border-radius: 50%; object-fit: cover; border: 4px solid #ffffff;
    box-shadow: 0 4px 12px rgba(120,20,30,0.25); background: #fffaf8;
  }
  .frill {
    position: relative; z-index: 2; height: 15px; margin-top: -1px;
    background: radial-gradient(circle at 10px 0, #ffffff 0 9px, #e8aab0 9px 10.5px, transparent 11px) 0 0 / 20px 15px repeat-x;
  }
  .body { position: relative; z-index: 1; padding: 14px 22px 4px 22px; }
  .body.has-illust { padding-top: 32px; }
  .section-h {
    display: flex; align-items: center; gap: 8px; margin: 4px 2px 10px 2px;
    font-size: 16px; font-weight: 900; color: #b81f30; letter-spacing: 2px;
  }
  .section-h::after { content: ""; flex: 1; border-bottom: 1.5px dashed #ecc3c6; }
  .shrine { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 18px; }
  .ofuda {
    position: relative; display: flex; gap: 12px; align-items: center; padding: 10px 14px 10px 10px;
    background: #fffdf6; border: 1.5px solid #d6303f; outline: 3px solid #fffdf6;
    box-shadow: 0 5px 14px rgba(170,60,70,0.14); border-radius: 3px;
  }
  .ofuda::before {
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 6px; background: #d6303f;
  }
  .thumb {
    flex-shrink: 0; width: 76px; height: 76px; margin-left: 6px; border-radius: 4px; object-fit: cover;
    border: 2px solid #ffffff; box-shadow: 0 2px 8px rgba(120,20,30,0.22); background: #fbecea;
  }
  .thumb.icon { display: flex; align-items: center; justify-content: center; font-size: 36px; }
  .ofuda .info { flex: 1; min-width: 0; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 12px; margin-bottom: 16px; }
  .preset {
    position: relative; padding: 11px 14px 10px 18px; border-radius: 7px;
    background: rgba(255,255,255,0.96); border: 1px solid #f2d2d3;
    box-shadow: 0 3px 10px rgba(170,60,70,0.08);
  }
  .preset::before {
    content: ""; position: absolute; left: 0; top: 10px; bottom: 10px; width: 4px;
    border-radius: 0 3px 3px 0; background: #e0707b;
  }
  .preset-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
  .name { font-size: 16.5px; font-weight: 900; color: #a91d2c; }
  .flag {
    flex-shrink: 0; font-family: Consolas, Menlo, monospace; font-size: 11.5px; font-weight: 800;
    color: #c4202f; background: #fff1ef; padding: 3px 7px; border-radius: 3px;
  }
  .desc { margin-top: 6px; font-size: 13px; font-weight: 700; color: #6e5155; }
  .size { margin-top: 3px; font-size: 11.5px; color: #b98a8f; }
  .usage {
    position: relative; background: rgba(255,255,255,0.96); border-radius: 8px;
    padding: 13px 18px 12px 22px; margin-bottom: 12px;
    border: 1px solid #f2d2d3; box-shadow: 0 4px 14px rgba(170,60,70,0.10);
  }
  .usage::before {
    content: ""; position: absolute; left: 0; top: 11px; bottom: 11px; width: 5px;
    border-radius: 0 3px 3px 0; background: #d6303f;
  }
  .usage-h {
    font-size: 15.5px; font-weight: 900; color: #b81f30; letter-spacing: 1px;
    padding-bottom: 7px; margin-bottom: 4px; border-bottom: 1.5px dashed #f2cfd1;
  }
  .example {
    margin-top: 7px; padding: 7px 12px; border-radius: 4px; font-size: 13.5px;
    font-family: Consolas, "Microsoft YaHei", monospace; color: #6e3a40;
    background: #fdf1ef; border-left: 3px solid #e0707b;
  }
  .tip { margin-top: 9px; font-size: 12.5px; line-height: 1.7; color: #8a6a6e; }
  .footer {
    position: relative; z-index: 1; margin-top: 8px; padding: 10px 14px 12px 14px;
    display: flex; justify-content: center; align-items: center; gap: 10px;
    color: #fff3ee; font-size: 12.5px; letter-spacing: 2px; background: #c8283a;
  }
  .footer::before {
    content: ""; position: absolute; left: 0; right: 0; top: -12px; height: 12px;
    background: radial-gradient(circle at 10px 12px, #c8283a 0 9px, transparent 10px) 0 0 / 20px 12px repeat-x;
  }
</style>
</head>
<body>
<div class="card">
  <svg width="0" height="0" style="position:absolute" aria-hidden="true">
    <defs>
      <symbol id="yy" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="47" fill="#ffffff" stroke="#9e1b2a" stroke-width="4"/>
        <path d="M50 3 A47 47 0 0 1 50 97 A23.5 23.5 0 0 1 50 50 A23.5 23.5 0 0 0 50 3 Z" fill="#d6303f"/>
        <circle cx="50" cy="26.5" r="7" fill="#d6303f"/>
        <circle cx="50" cy="73.5" r="7" fill="#ffffff"/>
      </symbol>
    </defs>
  </svg>

  <div class="banner{% if illust %} has-illust{% endif %}">
    <svg class="orb" width="52" height="52" aria-hidden="true"><use href="#yy"/></svg>
    <div>
      <div class="title serif">云绘图快捷预设</div>
      <div class="subtitle">一条参数，换一身行头 · 文生图 / 图生图通用</div>
    </div>
    {% if illust %}<img class="illust" src="{{ illust }}"/>{% endif %}
  </div>
  <div class="frill"></div>

  <div class="body{% if illust %} has-illust{% endif %}">
    {% if reimu_items %}
    <div class="section-h serif">⛩️ 博丽神社限定</div>
    <div class="shrine">
      {% for item in reimu_items %}
      <div class="ofuda">
        {% if item.thumb %}<img class="thumb" src="{{ item.thumb }}"/>{% else %}<div class="thumb icon">{{ item.icon }}</div>{% endif %}
        <div class="info">
          <div class="preset-top">
            <span class="name serif">{{ item.name | e }}</span>
            <span class="flag">--{{ item.name | e }}</span>
          </div>
          <div class="desc">{{ item.desc | e }}</div>
          <div class="size">推荐尺寸 · {{ item.size | e }}</div>
        </div>
      </div>
      {% endfor %}
    </div>
    {% endif %}

    <div class="section-h serif">🎨 通用画风</div>
    <div class="grid">
      {% for item in items %}
      <div class="preset">
        <div class="preset-top">
          <span class="name">{{ item.icon }} {{ item.name | e }}</span>
          <span class="flag">--{{ item.name | e }}</span>
        </div>
        <div class="desc">{{ item.desc | e }}</div>
        <div class="size">推荐尺寸 · {{ item.size | e }}</div>
      </div>
      {% endfor %}
    </div>

    {% if imported_items %}
    <div class="section-h serif">📥 已导入</div>
    <div class="grid">
      {% for item in imported_items %}
      <div class="preset">
        <div class="preset-top">
          <span class="name">{{ item.icon | e }} {{ item.name | e }}</span>
          <span class="flag">--{{ item.name | e }}</span>
        </div>
        <div class="desc">{{ item.desc | e }}</div>
        <div class="size">推荐尺寸 · {{ item.size | e }}</div>
      </div>
      {% endfor %}
    </div>
    {% endif %}

    <div class="usage">
      <div class="usage-h serif">使用示例</div>
      <div class="example">/云绘图 银发少女，蓝色连衣裙 --巫女</div>
      <div class="example">/云绘图 银发少女 --预设 手办</div>
      <div class="example">引用或附带原图 → /变手办　　回复原图 → /云绘图 --符卡</div>
      <div class="tip">
        附带原图时会自动切换到云端图片编辑，尽量保留人物身份、脸部、服装、姿势与构图；
        默认沿用第一张原图分辨率，手动填写 --size 时以指定尺寸为准。
      </div>
    </div>
  </div>

  <div class="footer serif">
    <svg width="16" height="16" aria-hidden="true"><use href="#yy"/></svg>
    <span>博丽神社 ｜ 云端绘图会消耗对应接口额度，赛钱箱也欢迎投币～</span>
  </div>
</div>
</body>
</html>
"""

DAILY_ME_CARD_TMPL = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=1280, height=10"/>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; width: 100%; background: #fbefee; }
  body {
    width: 100vw;
    min-width: 900px;
    font-family: "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", "Noto Sans CJK SC", sans-serif;
    color: #4d3336;
  }
  .serif { font-family: "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "SimSun", serif; }
  .card {
    width: 100%;
    overflow: hidden;
    position: relative;
    background:
      radial-gradient(circle at 92% 70%, rgba(214,48,64,.07), transparent 26%),
      linear-gradient(180deg, #fffaf8 0%, #fdf3f1 60%, #fbecea 100%);
  }
  .banner {
    display: flex; justify-content: space-between; align-items: center; gap: 16px;
    padding: 30px 36px 32px; color: #fffaf6;
    background: linear-gradient(170deg, #df3646 0%, #c8283a 65%, #b11f31 100%);
  }
  .brand { display: flex; align-items: center; gap: 16px; }
  .orb { flex-shrink: 0; filter: drop-shadow(0 3px 4px rgba(90,10,20,.35)); }
  .title { font-size: 36px; font-weight: 900; letter-spacing: 3px; text-shadow: 0 2px 0 rgba(100,10,20,.35); }
  .subtitle { margin-top: 6px; font-size: 16px; color: #ffe1dc; letter-spacing: 2px; }
  .date {
    flex-shrink: 0; font-size: 17px; font-weight: 900; letter-spacing: 2px;
    padding: 8px 16px; color: #c4202f; background: #fffaf0;
    border: 2px solid #fffaf0; outline: 2px solid #d6303f; outline-offset: -6px;
    transform: rotate(-3deg);
  }
  .frill {
    height: 20px; margin-top: -1px;
    background: radial-gradient(circle at 13px 0, #ffffff 0 12px, #e8aab0 12px 14px, transparent 14.5px) 0 0 / 26px 20px repeat-x;
  }
  .main { padding: 18px 34px 8px; }
  .details {
    display: grid; grid-template-columns: 1fr 1fr; gap: 13px 16px;
    margin-bottom: 22px;
  }
  .item {
    position: relative; min-height: 76px; padding: 14px 18px 14px 24px; border-radius: 9px;
    background: rgba(255,255,255,.96); border: 1px solid #f2d2d3;
    box-shadow: 0 4px 14px rgba(170,60,70,.10);
  }
  .item::before {
    content: ""; position: absolute; left: 0; top: 13px; bottom: 13px; width: 6px;
    border-radius: 0 3px 3px 0; background: #d6303f;
  }
  .item.wide { grid-column: 1 / -1; }
  .label { font-size: 15px; font-weight: 900; color: #b81f30; letter-spacing: 2px; margin-bottom: 6px; }
  .value { font-size: 20px; line-height: 1.45; font-weight: 700; color: #5d3c40; }
  .preview-wrap {
    padding: 10px; border-radius: 6px;
    background: #fffdf6;
    border: 2px solid #d6303f; outline: 4px solid #fffdf6;
    box-shadow: 0 10px 30px rgba(150,40,50,.16);
  }
  .preview {
    display: block; width: 100%; max-height: 620px; object-fit: contain;
    border-radius: 3px; background: #fbecea;
  }
  .meta {
    margin-top: 18px; padding: 12px 16px; border-radius: 4px; border-left: 4px solid #e0707b;
    text-align: center; font-size: 15px; font-weight: 700; color: #8a6a6e;
    background: rgba(255,255,255,.8);
  }
  .footer {
    position: relative; margin-top: 26px; padding: 14px 20px 16px;
    display: flex; justify-content: center; align-items: center; gap: 12px;
    font-size: 16px; letter-spacing: 2px; color: #fff3ee; background: #c8283a;
  }
  .footer::before {
    content: ""; position: absolute; left: 0; right: 0; top: -14px; height: 14px;
    background: radial-gradient(circle at 13px 14px, #c8283a 0 11px, transparent 12px) 0 0 / 26px 14px repeat-x;
  }
</style>
</head>
<body>
  <div class="card">
    <svg width="0" height="0" style="position:absolute" aria-hidden="true">
      <defs>
        <symbol id="yy" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="47" fill="#ffffff" stroke="#9e1b2a" stroke-width="4"/>
          <path d="M50 3 A47 47 0 0 1 50 97 A23.5 23.5 0 0 1 50 50 A23.5 23.5 0 0 0 50 3 Z" fill="#d6303f"/>
          <circle cx="50" cy="26.5" r="7" fill="#d6303f"/>
          <circle cx="50" cy="73.5" r="7" fill="#ffffff"/>
        </symbol>
      </defs>
    </svg>
    <div class="banner">
      <div class="brand">
        <svg class="orb" width="60" height="60" aria-hidden="true"><use href="#yy"/></svg>
        <div>
          <div class="title serif">今日的二次元的你</div>
          <div class="subtitle">博丽神社 · 每日一签</div>
        </div>
      </div>
      <div class="date serif">{{ date }}</div>
    </div>
    <div class="frill"></div>
    <div class="main">
      <div class="details">
        {% for item in items %}
        <div class="item{% if item.wide %} wide{% endif %}">
          <div class="label serif">{{ item.label }}</div>
          <div class="value">{{ item.value }}</div>
        </div>
        {% endfor %}
      </div>
      <div class="preview-wrap">
        <img class="preview" src="{{ preview_data_uri }}"/>
      </div>
      <div class="meta">{{ meta }}</div>
    </div>
    <div class="footer serif">
      <svg width="18" height="18" aria-hidden="true"><use href="#yy"/></svg>
      <span>{{ footer }}</span>
    </div>
  </div>
</body>
</html>
"""



# 帮助卡片「神社」主题：朱红与和纸配色，鸟居、注连绳、纸垂、绘马与樱花瓣等通用神社元素。
# 与默认模板共用同一份数据（groups / params / examples / wf_line / mode_line / scale）。
SHRINE_HELP_TMPL = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width={{ (820 * (scale | default(2))) | int }}, height=10"/>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    font-family: "PingFang SC","Microsoft YaHei","Hiragino Sans GB","Noto Sans CJK SC",sans-serif;
    background: #f6efe2;
  }
  .card {
    width: 820px; zoom: {{ scale | default(2) }}; position: relative; overflow: hidden; color: #4a3a32;
    background:
      radial-gradient(circle at 0 100%, transparent 18px, rgba(200,52,43,0.045) 19px, transparent 21px) 0 0 / 40px 20px,
      radial-gradient(circle at 20px 100%, transparent 18px, rgba(200,52,43,0.045) 19px, transparent 21px) 0 10px / 40px 20px,
      linear-gradient(180deg, #fbf6ec 0%, #f7efe0 60%, #f3e8d5 100%);
  }
  .serif { font-family: "Noto Serif CJK SC","Source Han Serif SC","Songti SC","SimSun",serif; }

  /* 顶部朱红横幅 */
  .banner {
    position: relative; padding: 26px 34px 34px 34px; color: #fff8ec;
    background: linear-gradient(170deg, #cf3a2f 0%, #b52c24 70%, #a3271f 100%);
  }
  .banner::after {
    content: ""; position: absolute; left: 0; right: 0; bottom: -1px; height: 14px;
    background: radial-gradient(circle at 10px -4px, transparent 12px, #fbf6ec 13px) 0 0 / 20px 14px repeat-x;
  }
  .hd { display: flex; justify-content: space-between; align-items: center; }
  .hd-l { display: flex; align-items: center; gap: 16px; }
  .title { font-size: 31px; font-weight: 900; letter-spacing: 3px; text-shadow: 0 2px 0 rgba(90,16,12,0.35); }
  .subtitle { font-size: 14px; color: #ffe2cf; margin-top: 6px; letter-spacing: 1px; }

  /* 绘马牌徽记 */
  .ema {
    position: relative; width: 104px; padding: 18px 8px 10px 8px; text-align: center;
    background: linear-gradient(180deg, #e9c98f 0%, #d9b06c 100%); color: #5b3a1c;
    clip-path: polygon(50% 0, 100% 22%, 100% 100%, 0 100%, 0 22%);
    box-shadow: inset 0 0 0 3px rgba(120,72,30,0.25);
  }
  .ema::before {
    content: ""; position: absolute; top: 7px; left: 50%; width: 8px; height: 8px; margin-left: -4px;
    border-radius: 50%; background: #7a4b22;
  }
  .ema-t { font-size: 20px; font-weight: 900; letter-spacing: 6px; line-height: 1.1; }
  .ema-s { font-size: 10.5px; font-weight: 700; letter-spacing: 2px; margin-top: 4px; color: #8a5a2b; }

  /* 注连绳与纸垂 */
  .rope { display: block; width: 820px; height: 58px; margin-top: -6px; position: relative; z-index: 2; }

  .petal {
    position: absolute; width: 14px; height: 10px; border-radius: 70% 0 70% 0;
    background: linear-gradient(135deg, #f7c6cc, #ee9fab); opacity: 0.75; pointer-events: none;
  }

  .body { position: relative; z-index: 1; padding: 2px 26px 6px 26px; }
  .group {
    position: relative; background: rgba(255,253,248,0.94); border-radius: 6px;
    padding: 16px 22px 14px 26px; margin-bottom: 15px;
    border: 1px solid #ecdcc4; box-shadow: 0 4px 14px rgba(140,90,40,0.10);
  }
  .group::before {
    content: ""; position: absolute; left: 0; top: 12px; bottom: 12px; width: 5px;
    border-radius: 0 3px 3px 0; background: #c8342b;
  }
  .group-h {
    font-size: 17px; font-weight: 900; color: #a8291f; letter-spacing: 1px;
    padding-bottom: 8px; margin-bottom: 8px; border-bottom: 1.5px solid #f0e2cc;
  }
  .cmd { display: flex; align-items: baseline; gap: 12px; padding: 6px 2px; }
  .cmd + .cmd { border-top: 1px dashed #f0e2cc; }
  .cmd-name { flex-shrink: 0; min-width: 196px; font-weight: 800; font-size: 14.5px; color: #8e2a20; }
  .cmd-desc { flex: 1; font-size: 13px; line-height: 1.55; color: #6b5548; }
  .cmd-tag {
    flex-shrink: 0; align-self: center; font-size: 10.5px; font-weight: 900; letter-spacing: 1px;
    padding: 2px 6px; border-radius: 4px; color: #c8342b; border: 1.5px solid #c8342b;
    transform: rotate(-4deg); background: rgba(200,52,43,0.06);
  }
  .pgrid { display: flex; flex-wrap: wrap; gap: 8px 18px; }
  .pi { width: 47%; display: flex; align-items: baseline; gap: 9px; padding: 4px 0; }
  .pn {
    flex-shrink: 0; font-family: Consolas, Menlo, monospace; font-size: 12.5px; font-weight: 700;
    background: #fff6ea; color: #9e2e22; padding: 2px 8px; border-radius: 4px; border: 1px solid #ebc9a8;
  }
  .pd { font-size: 12.5px; color: #6b5548; }
  .ex {
    border-radius: 4px; padding: 10px 15px;
    background: repeating-linear-gradient(180deg, #fffaf1 0, #fffaf1 25px, #f1e4cf 25px, #f1e4cf 26px);
  }
  .ex-l { font-family: Consolas, Menlo, monospace; font-size: 13px; color: #4a3a32; line-height: 26px; }
  .info { text-align: center; font-size: 12.5px; color: #8a6e5c; margin: 6px 0 2px 0; line-height: 1.8; }
  .footer {
    position: relative; z-index: 1; text-align: center; padding: 15px; margin-top: 8px;
    color: #fff1e2; font-size: 13px; letter-spacing: 2px; background: #b52c24;
  }
</style>
</head>
<body>
<div class="card">
  <span class="petal" style="top:250px;left:760px;transform:rotate(25deg);"></span>
  <span class="petal" style="top:420px;left:14px;transform:rotate(-30deg);"></span>
  <span class="petal" style="top:640px;left:790px;transform:rotate(60deg);width:11px;height:8px;"></span>
  <span class="petal" style="bottom:210px;left:22px;transform:rotate(15deg);"></span>
  <span class="petal" style="bottom:90px;left:780px;transform:rotate(-50deg);width:12px;height:9px;"></span>

  <div class="banner">
    <div class="hd">
      <div class="hd-l">
        <svg width="74" height="62" viewBox="0 0 120 100" aria-hidden="true">
          <path d="M2 13 Q60 1 118 13 L116 22 Q60 11 4 22 Z" fill="#fff4e4"/>
          <rect x="13" y="22" width="94" height="6" fill="#3a2420" opacity="0.55"/>
          <rect x="17" y="35" width="86" height="7" rx="1" fill="#fff4e4"/>
          <rect x="55" y="27" width="10" height="9" fill="#fff4e4"/>
          <rect x="27" y="22" width="10" height="72" fill="#fff4e4"/>
          <rect x="83" y="22" width="10" height="72" fill="#fff4e4"/>
          <rect x="23" y="90" width="18" height="7" rx="1" fill="#3a2420" opacity="0.55"/>
          <rect x="79" y="90" width="18" height="7" rx="1" fill="#3a2420" opacity="0.55"/>
        </svg>
        <div>
          <div class="title serif">绘马堂 · 绘图帮助</div>
          <div class="subtitle">写下心愿，交给画笔来实现～</div>
        </div>
      </div>
      <div class="ema serif">
        <div class="ema-t">奉纳</div>
        <div class="ema-s">绘 马 堂</div>
      </div>
    </div>
  </div>

  <svg class="rope" viewBox="0 0 820 58" aria-hidden="true">
    <path d="M0 10 Q205 30 410 14 T820 10" fill="none" stroke="#b98c4e" stroke-width="9" stroke-linecap="round"/>
    <path d="M0 10 Q205 30 410 14 T820 10" fill="none" stroke="#e2c58f" stroke-width="9"
          stroke-dasharray="7 9" stroke-linecap="round"/>
    {% for x in [150, 330, 490, 670] %}
    <polyline points="{{ x }},20 {{ x + 9 }},20 {{ x + 2 }},31 {{ x + 11 }},31 {{ x + 4 }},43 {{ x + 13 }},43 {{ x + 6 }},55"
              fill="none" stroke="#bfa98a" stroke-width="8" stroke-linejoin="round"/>
    <polyline points="{{ x }},20 {{ x + 9 }},20 {{ x + 2 }},31 {{ x + 11 }},31 {{ x + 4 }},43 {{ x + 13 }},43 {{ x + 6 }},55"
              fill="none" stroke="#ffffff" stroke-width="5" stroke-linejoin="round"/>
    {% endfor %}
  </svg>

  <div class="body">
    {% for g in groups %}
    <div class="group">
      <div class="group-h serif">{{ g.title }}</div>
      {% for c in g['items'] %}
      <div class="cmd"><span class="cmd-name">{{ c.cmd }}</span><span class="cmd-desc">{{ c.desc }}</span>{% if c.admin %}<span class="cmd-tag">管理员</span>{% endif %}</div>
      {% endfor %}
    </div>
    {% endfor %}

    <div class="group">
      <div class="group-h serif">&#127899;&#65039; 可选参数（跟在提示词后，均可省略）</div>
      <div class="pgrid">
        {% for p in params %}<div class="pi"><span class="pn">{{ p.name }}</span><span class="pd">{{ p.desc }}</span></div>{% endfor %}
      </div>
    </div>

    <div class="group">
      <div class="group-h serif">&#128221; 示例</div>
      <div class="ex">{% for e in examples %}<div class="ex-l">{{ e }}</div>{% endfor %}</div>
    </div>

    <div class="info">{{ wf_line }}<br/>{{ mode_line }}</div>
  </div>

  <div class="footer serif">&#127800; 绘马堂 ｜ 愿今日所绘，皆如所愿。</div>
</div>
</body>
</html>
"""

# 帮助卡片「博丽灵梦」主题：红白巫女配色，大红蝴蝶结、阴阳玉、符札、御币与赛钱箱。
# 与默认模板共用同一份数据（groups / params / examples / wf_line / mode_line / scale）。
REIMU_HELP_TMPL = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width={{ (820 * (scale | default(2))) | int }}, height=10"/>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    font-family: "PingFang SC","Microsoft YaHei","Hiragino Sans GB","Noto Sans CJK SC",sans-serif;
    background: #fbefee;
  }
  .card {
    width: 820px; zoom: {{ scale | default(2) }}; position: relative; overflow: hidden; color: #4d3336;
    background:
      radial-gradient(circle at 6% 30%, rgba(214,48,64,0.07), transparent 22%),
      radial-gradient(circle at 96% 62%, rgba(214,48,64,0.07), transparent 24%),
      linear-gradient(180deg, #fffaf8 0%, #fdf3f1 55%, #fbecea 100%);
  }
  .serif { font-family: "Noto Serif CJK SC","Source Han Serif SC","Songti SC","SimSun",serif; }

  /* 顶部红色横幅 + 白色荷叶边 */
  .banner {
    position: relative; padding: 26px 34px 30px 30px; color: #fffaf6;
    background: linear-gradient(170deg, #df3646 0%, #c8283a 65%, #b11f31 100%);
  }
  .frill {
    position: relative; z-index: 2; height: 15px; margin-top: -1px;
    background: radial-gradient(circle at 10px 0, #ffffff 0 9px, #e8aab0 9px 10.5px, transparent 11px) 0 0 / 20px 15px repeat-x;
  }
  .hd { display: flex; justify-content: space-between; align-items: center; }
  .hd-l { display: flex; align-items: center; gap: 16px; }
  .orb { filter: drop-shadow(0 3px 4px rgba(90,10,20,0.35)); }
  .title { font-size: 31px; font-weight: 900; letter-spacing: 3px; text-shadow: 0 2px 0 rgba(100,10,20,0.35); }
  .subtitle { font-size: 14px; color: #ffe1dc; margin-top: 6px; letter-spacing: 1px; }

  /* 赛钱箱徽记 */
  .box { width: 112px; text-align: center; color: #fff3dc; }
  .illust {
    width: 132px; height: 132px; margin: -14px -8px -44px 0; position: relative; z-index: 4;
    border-radius: 50%; object-fit: cover; border: 4px solid #ffffff; background: #fffaf8;
    box-shadow: 0 4px 12px rgba(120,20,30,0.25);
  }
  .box-lid {
    height: 12px; margin: 0 -6px; border-radius: 3px 3px 0 0;
    background: linear-gradient(180deg, #9a6233, #7b4a24);
    box-shadow: 0 2px 0 rgba(0,0,0,0.18);
  }
  .box-slat {
    height: 14px;
    background: repeating-linear-gradient(90deg, #5b3518 0 7px, #c08850 7px 12px);
    border-left: 4px solid #6e421f; border-right: 4px solid #6e421f;
  }
  .box-body {
    padding: 6px 4px 7px 4px; border-radius: 0 0 3px 3px;
    background: linear-gradient(180deg, #a86e3c 0%, #8a5428 100%);
    border: 4px solid #6e421f; border-top: none;
  }
  .box-t { font-size: 22px; font-weight: 900; letter-spacing: 6px; line-height: 1.15; }
  .box-s { font-size: 9.5px; font-weight: 700; letter-spacing: 2px; color: #f3d6a8; }

  /* 蝴蝶结 */
  .bow { display: block; width: 210px; height: 96px; margin: -50px auto -12px auto; position: relative; z-index: 3; }

  .deco { position: absolute; pointer-events: none; }
  .ofuda {
    width: 18px; height: 48px; padding-top: 4px; text-align: center; opacity: 0.5;
    background: #fffaf0; border: 1.5px solid #d6303f; outline: 1px solid #fffaf0;
    font-size: 10px; font-weight: 900; color: #c4202f; line-height: 1.15;
    box-shadow: 0 2px 5px rgba(150,40,50,0.15);
  }

  .body { position: relative; z-index: 1; padding: 6px 26px 6px 26px; }
  .group {
    position: relative; background: rgba(255,255,255,0.96); border-radius: 8px;
    padding: 16px 22px 14px 26px; margin-bottom: 15px;
    border: 1px solid #f2d2d3; box-shadow: 0 4px 14px rgba(170,60,70,0.10);
  }
  .group::before {
    content: ""; position: absolute; left: 0; top: 12px; bottom: 12px; width: 5px;
    border-radius: 0 3px 3px 0; background: #d6303f;
  }
  .g-orb { position: absolute; top: 12px; right: 16px; width: 26px; height: 26px; opacity: 0.22; }
  .group-h {
    font-size: 17px; font-weight: 900; color: #b81f30; letter-spacing: 1px;
    padding-bottom: 8px; margin-bottom: 8px; border-bottom: 1.5px dashed #f2cfd1;
  }
  .cmd { display: flex; align-items: baseline; gap: 12px; padding: 6px 2px; }
  .cmd + .cmd { border-top: 1px solid #f8e6e6; }
  .cmd-name { flex-shrink: 0; min-width: 196px; font-weight: 800; font-size: 14.5px; color: #a91d2c; }
  .cmd-desc { flex: 1; font-size: 13px; line-height: 1.55; color: #6e5155; }
  .cmd-tag {
    flex-shrink: 0; align-self: center; font-size: 10.5px; font-weight: 900; letter-spacing: 1px;
    padding: 2px 6px; border-radius: 2px; color: #c4202f; background: #fffaf0;
    border: 1.5px solid #d6303f; outline: 1px solid #fffaf0; transform: rotate(-4deg);
  }
  .pgrid { display: flex; flex-wrap: wrap; gap: 8px 18px; }
  .pi { width: 47%; display: flex; align-items: baseline; gap: 9px; padding: 4px 0; }
  .pn {
    flex-shrink: 0; font-family: Consolas, Menlo, monospace; font-size: 12.5px; font-weight: 700;
    background: #fff0f0; color: #b8202f; padding: 2px 8px; border-radius: 4px; border: 1px solid #f2c2c6;
  }
  .pd { font-size: 12.5px; color: #6e5155; }
  .ex {
    border-radius: 4px; padding: 10px 15px; border-left: 3px solid #e0707b;
    background: repeating-linear-gradient(180deg, #fffdfb 0, #fffdfb 25px, #f6e1e1 25px, #f6e1e1 26px);
  }
  .ex-l { font-family: Consolas, Menlo, monospace; font-size: 13px; color: #4d3336; line-height: 26px; }
  .info { text-align: center; font-size: 12.5px; color: #a07479; margin: 6px 0 2px 0; line-height: 1.8; }
  .footer {
    position: relative; z-index: 1; margin-top: 10px; padding: 12px 15px 14px 15px;
    display: flex; justify-content: center; align-items: center; gap: 12px;
    color: #fff3ee; font-size: 13px; letter-spacing: 2px; background: #c8283a;
  }
  .footer::before {
    content: ""; position: absolute; left: 0; right: 0; top: -12px; height: 12px;
    background: radial-gradient(circle at 10px 12px, #c8283a 0 9px, transparent 10px) 0 0 / 20px 12px repeat-x;
  }
</style>
</head>
<body>
<div class="card">
  <svg width="0" height="0" style="position:absolute" aria-hidden="true">
    <defs>
      <symbol id="yy" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="47" fill="#ffffff" stroke="#9e1b2a" stroke-width="4"/>
        <path d="M50 3 A47 47 0 0 1 50 97 A23.5 23.5 0 0 1 50 50 A23.5 23.5 0 0 0 50 3 Z" fill="#d6303f"/>
        <circle cx="50" cy="26.5" r="7" fill="#d6303f"/>
        <circle cx="50" cy="73.5" r="7" fill="#ffffff"/>
      </symbol>
      <symbol id="lobe" viewBox="0 0 120 96">
        <path d="M118 44 C96 10 40 -2 14 14 C-2 26 6 64 26 78 C52 92 92 72 118 56 Z"
              fill="#d6303f" stroke="#ffffff" stroke-width="7" stroke-linejoin="round"/>
        <path d="M110 46 C88 22 48 14 26 24" fill="none" stroke="#a91d2c" stroke-width="3" stroke-linecap="round" opacity="0.6"/>
        <path d="M108 54 C84 64 54 74 34 66" fill="none" stroke="#a91d2c" stroke-width="3" stroke-linecap="round" opacity="0.6"/>
      </symbol>
    </defs>
  </svg>

  <div class="deco ofuda serif" style="top:300px;left:8px;transform:rotate(-12deg);">博<br/>麗</div>
  <div class="deco ofuda serif" style="top:560px;right:6px;transform:rotate(14deg);">封<br/>魔</div>
  <div class="deco ofuda serif" style="bottom:170px;left:6px;transform:rotate(8deg);">退<br/>治</div>
  <svg class="deco" style="top:430px;right:4px;width:20px;height:20px;opacity:0.35;"><use href="#yy"/></svg>
  <svg class="deco" style="bottom:300px;left:4px;width:16px;height:16px;opacity:0.3;"><use href="#yy"/></svg>

  <div class="banner">
    <div class="hd">
      <div class="hd-l">
        <svg class="orb" width="66" height="66" aria-hidden="true"><use href="#yy"/></svg>
        <div>
          <div class="title serif">博丽神社 · 绘图帮助</div>
          <div class="subtitle">乐园的巫女今天也在认真画画（大概）～</div>
        </div>
      </div>
      {% if illust %}
      <img class="illust" src="{{ illust }}"/>
      {% else %}
      <div class="box serif">
        <div class="box-lid"></div>
        <div class="box-slat"></div>
        <div class="box-body">
          <div class="box-t">赛钱</div>
          <div class="box-s">SAISEN BOX</div>
        </div>
      </div>
      {% endif %}
    </div>
  </div>
  <div class="frill"></div>

  <svg class="bow" viewBox="0 0 240 110" aria-hidden="true">
    <path d="M112 60 L92 106 L104 100 L110 110 L122 64 Z" fill="#c8283a" stroke="#ffffff" stroke-width="4" stroke-linejoin="round"/>
    <path d="M128 60 L148 106 L136 100 L130 110 L118 64 Z" fill="#c8283a" stroke="#ffffff" stroke-width="4" stroke-linejoin="round"/>
    <use href="#lobe" x="2" y="4" width="120" height="96"/>
    <use href="#lobe" x="2" y="4" width="120" height="96" transform="translate(240,0) scale(-1,1)"/>
    <rect x="106" y="38" width="28" height="32" rx="9" fill="#c8283a" stroke="#ffffff" stroke-width="5"/>
  </svg>

  <div class="body">
    {% for g in groups %}
    <div class="group">
      <svg class="g-orb" aria-hidden="true"><use href="#yy"/></svg>
      <div class="group-h serif">{{ g.title }}</div>
      {% for c in g['items'] %}
      <div class="cmd"><span class="cmd-name">{{ c.cmd }}</span><span class="cmd-desc">{{ c.desc }}</span>{% if c.admin %}<span class="cmd-tag">管理员</span>{% endif %}</div>
      {% endfor %}
    </div>
    {% endfor %}

    <div class="group">
      <svg class="g-orb" aria-hidden="true"><use href="#yy"/></svg>
      <div class="group-h serif">&#127899;&#65039; 可选参数（跟在提示词后，均可省略）</div>
      <div class="pgrid">
        {% for p in params %}<div class="pi"><span class="pn">{{ p.name }}</span><span class="pd">{{ p.desc }}</span></div>{% endfor %}
      </div>
    </div>

    <div class="group">
      <svg class="g-orb" aria-hidden="true"><use href="#yy"/></svg>
      <div class="group-h serif">&#128221; 示例</div>
      <div class="ex">{% for e in examples %}<div class="ex-l">{{ e }}</div>{% endfor %}</div>
    </div>

    <div class="info">{{ wf_line }}<br/>{{ mode_line }}</div>
  </div>

  <div class="footer serif">
    <svg width="18" height="18" aria-hidden="true"><use href="#yy"/></svg>
    <span>博丽神社 ｜ 赛钱箱就在门口，画完记得投点香火钱哦～</span>
  </div>
</div>
</body>
</html>
"""


# 博丽灵梦风格的通用信息卡片：/绘图列表、/绘图状态、/云绘图切换、/绘图主题 共用。
# 数据：title, subtitle, sections=[{title, rows=[{name, desc, tag}], lines=[...]}], tips=[...], illust（可选 data URI）
REIMU_INFO_CARD_TMPL = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width={{ (640 * (scale | default(2))) | int }}, height=10"/>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    font-family: "PingFang SC","Microsoft YaHei","Hiragino Sans GB","Noto Sans CJK SC",sans-serif;
    background: #fbefee;
  }
  .card {
    width: 640px; zoom: {{ scale | default(2) }}; position: relative; overflow: hidden; color: #4d3336;
    background:
      radial-gradient(circle at 92% 70%, rgba(214,48,64,0.07), transparent 26%),
      linear-gradient(180deg, #fffaf8 0%, #fdf3f1 60%, #fbecea 100%);
  }
  .serif { font-family: "Noto Serif CJK SC","Source Han Serif SC","Songti SC","SimSun",serif; }
  .banner {
    position: relative; min-height: 104px; padding: 22px 26px 24px 26px; color: #fffaf6;
    background: linear-gradient(170deg, #df3646 0%, #c8283a 65%, #b11f31 100%);
    display: flex; align-items: center; gap: 14px;
  }
  .banner.has-illust { padding-right: 150px; }
  .orb { flex-shrink: 0; filter: drop-shadow(0 3px 4px rgba(90,10,20,0.35)); }
  .title { font-size: 25px; font-weight: 900; letter-spacing: 2px; text-shadow: 0 2px 0 rgba(100,10,20,0.35); }
  .subtitle { font-size: 13px; color: #ffe1dc; margin-top: 5px; letter-spacing: 1px; }
  .illust {
    position: absolute; right: 12px; bottom: -34px; width: 136px; height: 136px; z-index: 3;
    border-radius: 50%; object-fit: cover; border: 4px solid #ffffff;
    box-shadow: 0 4px 12px rgba(120,20,30,0.25); background: #fffaf8;
  }
  .frill {
    position: relative; z-index: 2; height: 15px; margin-top: -1px;
    background: radial-gradient(circle at 10px 0, #ffffff 0 9px, #e8aab0 9px 10.5px, transparent 11px) 0 0 / 20px 15px repeat-x;
  }
  .body { position: relative; z-index: 1; padding: 14px 22px 4px 22px; }
  .body.has-illust { padding-top: 30px; }
  .group {
    position: relative; background: rgba(255,255,255,0.96); border-radius: 8px;
    padding: 13px 18px 11px 22px; margin-bottom: 13px;
    border: 1px solid #f2d2d3; box-shadow: 0 4px 14px rgba(170,60,70,0.10);
  }
  .group::before {
    content: ""; position: absolute; left: 0; top: 11px; bottom: 11px; width: 5px;
    border-radius: 0 3px 3px 0; background: #d6303f;
  }
  .group-h {
    font-size: 15.5px; font-weight: 900; color: #b81f30; letter-spacing: 1px;
    padding-bottom: 7px; margin-bottom: 6px; border-bottom: 1.5px dashed #f2cfd1;
  }
  .row { display: flex; align-items: baseline; gap: 10px; padding: 5px 2px; }
  .row + .row { border-top: 1px solid #f8e6e6; }
  .row-name { flex-shrink: 0; min-width: 120px; font-weight: 800; font-size: 14px; color: #a91d2c; }
  .row-desc { flex: 1; font-size: 13px; line-height: 1.55; color: #6e5155; word-break: break-all; }
  .tag {
    flex-shrink: 0; align-self: center; font-size: 10.5px; font-weight: 900; letter-spacing: 1px;
    padding: 2px 6px; border-radius: 2px; color: #c4202f; background: #fffaf0;
    border: 1.5px solid #d6303f; outline: 1px solid #fffaf0; transform: rotate(-4deg);
  }
  .line { font-size: 13px; line-height: 1.7; color: #6e5155; padding: 1px 2px; }
  .tips {
    border-radius: 4px; padding: 8px 14px; margin-bottom: 12px; border-left: 3px solid #e0707b;
    background: repeating-linear-gradient(180deg, #fffdfb 0, #fffdfb 23px, #f6e1e1 23px, #f6e1e1 24px);
  }
  .tip { font-size: 12.5px; color: #6e5155; line-height: 24px; }
  .footer {
    position: relative; z-index: 1; margin-top: 8px; padding: 10px 14px 12px 14px;
    display: flex; justify-content: center; align-items: center; gap: 10px;
    color: #fff3ee; font-size: 12.5px; letter-spacing: 2px; background: #c8283a;
  }
  .footer::before {
    content: ""; position: absolute; left: 0; right: 0; top: -12px; height: 12px;
    background: radial-gradient(circle at 10px 12px, #c8283a 0 9px, transparent 10px) 0 0 / 20px 12px repeat-x;
  }
</style>
</head>
<body>
<div class="card">
  <svg width="0" height="0" style="position:absolute" aria-hidden="true">
    <defs>
      <symbol id="yy" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="47" fill="#ffffff" stroke="#9e1b2a" stroke-width="4"/>
        <path d="M50 3 A47 47 0 0 1 50 97 A23.5 23.5 0 0 1 50 50 A23.5 23.5 0 0 0 50 3 Z" fill="#d6303f"/>
        <circle cx="50" cy="26.5" r="7" fill="#d6303f"/>
        <circle cx="50" cy="73.5" r="7" fill="#ffffff"/>
      </symbol>
    </defs>
  </svg>

  <div class="banner{% if illust %} has-illust{% endif %}">
    <svg class="orb" width="52" height="52" aria-hidden="true"><use href="#yy"/></svg>
    <div>
      <div class="title serif">{{ title | e }}</div>
      {% if subtitle %}<div class="subtitle">{{ subtitle | e }}</div>{% endif %}
    </div>
    {% if illust %}<img class="illust" src="{{ illust }}"/>{% endif %}
  </div>
  <div class="frill"></div>

  <div class="body{% if illust %} has-illust{% endif %}">
    {% for s in sections %}
    <div class="group">
      <div class="group-h serif">{{ s.title | e }}</div>
      {% for r in s['rows'] or [] %}
      <div class="row"><span class="row-name">{{ r.name | e }}</span><span class="row-desc">{{ r.desc | e }}</span>{% if r.tag %}<span class="tag">{{ r.tag | e }}</span>{% endif %}</div>
      {% endfor %}
      {% for l in s['lines'] or [] %}<div class="line">{{ l | e }}</div>{% endfor %}
    </div>
    {% endfor %}
    {% if tips %}
    <div class="tips">{% for t in tips %}<div class="tip">{{ t | e }}</div>{% endfor %}</div>
    {% endif %}
  </div>

  <div class="footer serif">
    <svg width="16" height="16" aria-hidden="true"><use href="#yy"/></svg>
    <span>{{ footer | default("博丽神社 ｜ 有事就来神社找巫女吧～") | e }}</span>
  </div>
</div>
</body>
</html>
"""


# 博丽灵梦风格的小提示卡：把普通文字回复（报错、权限、切换结果、用法等）渲染成图片。
# 数据：kind（ok / error / warn / info）, label, lines=[...], illust（可选 data URI）
REIMU_NOTICE_CARD_TMPL = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width={{ (540 * (scale | default(2))) | int }}, height=10"/>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    font-family: "PingFang SC","Microsoft YaHei","Hiragino Sans GB","Noto Sans CJK SC",sans-serif;
    background: #fbefee;
  }
  .serif { font-family: "Noto Serif CJK SC","Source Han Serif SC","Songti SC","SimSun",serif; }
  .card {
    width: 540px; zoom: {{ scale | default(2) }}; position: relative; overflow: hidden; color: #4d3336;
    background: linear-gradient(180deg, #fffaf8 0%, #fdf3f1 100%);
    border-top: 10px solid #c8283a;
  }
  .card.error { border-top-color: #9e1b2a; }
  .card.warn { border-top-color: #d89a1c; }
  .frill {
    height: 12px;
    background: radial-gradient(circle at 10px 0, #c8283a 0 8px, transparent 9px) 0 0 / 20px 12px repeat-x;
  }
  .card.error .frill { background-image: radial-gradient(circle at 10px 0, #9e1b2a 0 8px, transparent 9px); }
  .card.warn .frill { background-image: radial-gradient(circle at 10px 0, #d89a1c 0 8px, transparent 9px); }
  .main { display: flex; gap: 16px; align-items: flex-start; padding: 8px 22px 16px 18px; }
  .avatar {
    flex-shrink: 0; width: 76px; height: 76px; border-radius: 50%; object-fit: cover;
    border: 3px solid #ffffff; box-shadow: 0 3px 10px rgba(150,40,50,0.22); background: #fffaf8;
  }
  .orb { flex-shrink: 0; width: 60px; height: 60px; margin: 6px 8px 0 8px; filter: drop-shadow(0 3px 4px rgba(90,10,20,0.25)); }
  .content { flex: 1; min-width: 0; padding-top: 4px; }
  .label {
    display: inline-block; font-size: 12px; font-weight: 900; letter-spacing: 2px; margin-bottom: 8px;
    padding: 2px 8px; border-radius: 2px; color: #c4202f; background: #fffaf0;
    border: 1.5px solid #d6303f; outline: 1px solid #fffaf0; transform: rotate(-3deg);
  }
  .card.error .label { color: #ffffff; background: #9e1b2a; border-color: #9e1b2a; }
  .card.warn .label { color: #8a5a00; background: #fff5dc; border-color: #d89a1c; }
  .line { font-size: 14px; line-height: 1.65; color: #4d3336; white-space: pre-wrap; word-break: break-all; }
  .line.first { font-size: 15px; font-weight: 700; color: #a91d2c; }
  .card.error .line.first { color: #8e1424; }
  .card.warn .line.first { color: #8a5a00; }
  .line.blank { height: 8px; }
  .sign { text-align: right; font-size: 11px; color: #c49a9e; letter-spacing: 2px; padding: 0 16px 10px 0; }
</style>
</head>
<body>
<div class="card {{ kind | default('info') | e }}">
  <svg width="0" height="0" style="position:absolute" aria-hidden="true">
    <defs>
      <symbol id="yy" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="47" fill="#ffffff" stroke="#9e1b2a" stroke-width="4"/>
        <path d="M50 3 A47 47 0 0 1 50 97 A23.5 23.5 0 0 1 50 50 A23.5 23.5 0 0 0 50 3 Z" fill="#d6303f"/>
        <circle cx="50" cy="26.5" r="7" fill="#d6303f"/>
        <circle cx="50" cy="73.5" r="7" fill="#ffffff"/>
      </symbol>
    </defs>
  </svg>
  <div class="frill"></div>
  <div class="main">
    {% if illust %}<img class="avatar" src="{{ illust }}"/>{% else %}<svg class="orb" aria-hidden="true"><use href="#yy"/></svg>{% endif %}
    <div class="content">
      <div class="label serif">{{ label | e }}</div>
      {% for l in lines %}{% if l %}<div class="line{% if loop.first %} first{% endif %}">{{ l | e }}</div>{% else %}<div class="line blank"></div>{% endif %}{% endfor %}
    </div>
  </div>
  <div class="sign serif">—— 博丽神社</div>
</div>
</body>
</html>
"""


# 帮助卡片可选主题：名称 -> (模板, 一句话说明)。第一个为默认主题。
HELP_CARD_THEMES = {
    "默认": (DRAW_HELP_TMPL, "淡紫蓝画室风格"),
    "神社": (SHRINE_HELP_TMPL, "朱红和纸、鸟居与注连绳的和风神社风格"),
    "博丽灵梦": (REIMU_HELP_TMPL, "红白巫女配色，蝴蝶结、阴阳玉、符札与赛钱箱的博丽神社风格"),
}
