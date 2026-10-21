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

CLOUD_PRESET_CARD_TMPL = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; width: 100%; background: transparent; }
  body {
    width: 100vw; min-width: 900px;
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
    color: #4e5878;
  }
  .card {
    width: 100%; padding: 34px 36px 28px; overflow: hidden;
    zoom: {{ scale | default(2) }};
    background:
      radial-gradient(circle at 5% 4%, rgba(255,190,219,.48), transparent 27%),
      radial-gradient(circle at 96% 5%, rgba(172,220,255,.58), transparent 29%),
      radial-gradient(circle at 92% 96%, rgba(205,190,255,.42), transparent 30%),
      linear-gradient(145deg, #fff9fc 0%, #f5f6ff 48%, #eff8ff 100%);
    border: 2px solid rgba(193,195,235,.72);
  }
  .top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
  .brand { display: flex; align-items: center; gap: 15px; }
  .logo {
    width: 58px; height: 58px; border-radius: 18px; display: flex;
    align-items: center; justify-content: center; font-size: 32px;
    background: linear-gradient(145deg, #7f8eea, #99b9f2);
    box-shadow: 0 9px 24px rgba(104,121,199,.25);
  }
  .title { font-size: 31px; font-weight: 900; color: #6573bd; letter-spacing: .5px; }
  .subtitle { margin-top: 4px; font-size: 15px; color: #8d96bd; }
  .badge {
    padding: 9px 15px; border-radius: 999px; font-size: 14px; font-weight: 800;
    color: #7d70ac; background: rgba(255,255,255,.72);
    border: 1px solid rgba(195,180,225,.68);
  }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 13px 15px; }
  .preset {
    min-height: 94px; padding: 16px 18px; border-radius: 19px;
    background: rgba(255,255,255,.82); border: 1px solid rgba(208,211,237,.82);
    box-shadow: 0 7px 22px rgba(94,105,158,.09);
  }
  .preset-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
  .name { font-size: 20px; font-weight: 900; color: #6573bd; }
  .flag {
    font-family: Consolas, Menlo, monospace; font-size: 13px; font-weight: 800;
    color: #6d80bd; background: #edf2ff; padding: 5px 9px; border-radius: 9px;
  }
  .desc { margin-top: 10px; font-size: 15.5px; font-weight: 700; color: #5f6884; }
  .size { margin-top: 5px; font-size: 13px; color: #9a86b4; }
  .usage {
    margin-top: 18px; padding: 20px 22px; border-radius: 21px;
    background: rgba(255,255,255,.75); border: 1px solid rgba(208,198,234,.76);
  }
  .usage-title { font-size: 18px; font-weight: 900; color: #746bb1; margin-bottom: 11px; }
  .example {
    margin-top: 8px; padding: 10px 13px; border-radius: 12px; font-size: 14.5px;
    font-family: Consolas, "Microsoft YaHei", monospace; color: #56648b;
    background: #f1f4fc; border-left: 4px solid #92a2df;
  }
  .tip { margin-top: 12px; font-size: 14px; line-height: 1.75; color: #7d86a6; }
  .footer { margin-top: 18px; text-align: center; font-size: 13.5px; color: #9aa3bf; }
</style>
</head>
<body>
  <div class="card">
    <div class="top">
      <div class="brand">
        <div class="logo">🎨</div>
        <div>
          <div class="title">云绘图快捷预设</div>
          <div class="subtitle">一条参数，快速切换成品风格</div>
        </div>
      </div>
      <div class="badge">云端绘图 · 文生图 / 图生图</div>
    </div>
    <div class="grid">
      {% for item in items %}
      <div class="preset">
        <div class="preset-top">
          <span class="name">{{ item.icon }} {{ item.name }}</span>
          <span class="flag">--{{ item.name }}</span>
        </div>
        <div class="desc">{{ item.desc }}</div>
        <div class="size">推荐尺寸 · {{ item.size }}</div>
      </div>
      {% endfor %}
    </div>
    <div class="usage">
      <div class="usage-title">✨ 使用示例</div>
      <div class="example">/云绘图 银发少女，蓝色连衣裙 --手办</div>
      <div class="example">引用或附带原图 → /变手办</div>
      <div class="example">回复原图 → /云绘图 --毛绒</div>
      <div class="tip">
        附带原图时会自动切换到云端图片编辑，尽量保留人物身份、脸部、服装、姿势与构图；
        默认沿用第一张原图分辨率，手动填写 --size 时以指定尺寸为准。
      </div>
    </div>
    <div class="footer">Rabbit House · 云端绘图会消耗对应接口额度</div>
  </div>
</body>
</html>
"""

DAILY_ME_CARD_TMPL = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; width: 100%; background: transparent; }
  body {
    width: 100vw;
    min-width: 900px;
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
    color: #665c83;
  }
  .card {
    width: 100%;
    padding: 34px;
    border-radius: 34px;
    overflow: hidden;
    background:
      radial-gradient(circle at 8% 4%, rgba(255,191,218,.52), transparent 25%),
      radial-gradient(circle at 94% 8%, rgba(178,222,255,.58), transparent 26%),
      radial-gradient(circle at 90% 94%, rgba(204,189,255,.46), transparent 30%),
      linear-gradient(145deg, #fff9fc 0%, #f8f4ff 48%, #f0f8ff 100%);
    border: 2px solid rgba(208,183,235,.75);
    box-shadow: 0 18px 55px rgba(100,83,140,.18);
  }
  .top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 22px; }
  .title { font-size: 34px; font-weight: 800; color: #806db0; letter-spacing: 1px; }
  .date {
    font-size: 16px; font-weight: 700; color: #9a89bd;
    padding: 9px 15px; border-radius: 999px;
    background: rgba(255,255,255,.72); border: 1px solid rgba(190,170,225,.5);
  }
  .details {
    display: grid; grid-template-columns: 1fr 1fr; gap: 13px 16px;
    margin-bottom: 22px;
  }
  .item {
    min-height: 76px; padding: 14px 17px; border-radius: 18px;
    background: rgba(255,255,255,.76); border: 1px solid rgba(220,204,238,.72);
  }
  .item.wide { grid-column: 1 / -1; }
  .label { font-size: 14px; font-weight: 800; color: #ac8fc7; margin-bottom: 6px; }
  .value { font-size: 20px; line-height: 1.45; font-weight: 700; color: #625778; }
  .preview-wrap {
    padding: 10px; border-radius: 26px;
    background: rgba(255,255,255,.86);
    border: 1px solid rgba(215,194,235,.8);
    box-shadow: 0 10px 30px rgba(98,77,135,.12);
  }
  .preview {
    display: block; width: 100%; max-height: 620px; object-fit: contain;
    border-radius: 19px; background: #f6f2fa;
  }
  .meta {
    margin-top: 17px; padding: 13px 16px; border-radius: 15px;
    text-align: center; font-size: 15px; font-weight: 700; color: #8c7ba8;
    background: rgba(255,255,255,.62);
  }
  .footer {
    margin-top: 15px; text-align: center; font-size: 15px; color: #a392bb;
  }
</style>
</head>
<body>
  <div class="card">
    <div class="top">
      <div class="title">✨ 今日的二次元的你</div>
      <div class="date">{{ date }}</div>
    </div>
    <div class="details">
      {% for item in items %}
      <div class="item{% if item.wide %} wide{% endif %}">
        <div class="label">{{ item.label }}</div>
        <div class="value">{{ item.value }}</div>
      </div>
      {% endfor %}
    </div>
    <div class="preview-wrap">
      <img class="preview" src="{{ preview_data_uri }}"/>
    </div>
    <div class="meta">{{ meta }}</div>
    <div class="footer">{{ footer }}</div>
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


# 帮助卡片可选主题：名称 -> (模板, 一句话说明)。第一个为默认主题。
HELP_CARD_THEMES = {
    "默认": (DRAW_HELP_TMPL, "淡紫蓝画室风格"),
    "神社": (SHRINE_HELP_TMPL, "朱红和纸、鸟居与注连绳的和风神社风格"),
}
