import asyncio
import base64
import json
import math
import os
import random
import tempfile
import time
import uuid

import aiohttp

from astrbot.api import logger, AstrBotConfig
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult, MessageChain
from astrbot.api.star import Context, Star
import astrbot.api.message_components as Comp


# å†…ç½®çš„ SD1.5 æ–‡ç”Ÿå›¾ç¤ºä¾‹å·¥ä½œæµï¼ˆAPI æ ¼å¼ï¼‰ã€‚
# å½“ç”¨æˆ·æ²¡æœ‰åœ¨é…ç½®é‡Œå¡«å†™ã€Œé»˜è®¤å·¥ä½œæµã€æ—¶ä½¿ç”¨è¿™ä¸€ä»½ã€‚
# å ä½ç¬¦å…¨éƒ¨ç”¨å¼•å·åŒ…è£¹ï¼Œä¿è¯å®ƒæœ¬èº«å°±æ˜¯åˆæ³• JSONã€‚
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
        <div class="title">æ™ºä¹ƒçš„ç”»å®¤ Â· ç»˜å›¾å¸®åŠ©</div>
        <div class="subtitle">æƒ³ç”»ç‚¹ä»€ä¹ˆï¼Ÿè¿™äº›éƒ½äº¤ç»™æ™ºä¹ƒå§ï½</div>
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
      <div class="cmd"><span class="cmd-name">{{ c.cmd }}</span><span class="cmd-desc">{{ c.desc }}</span>{% if c.admin %}<span class="cmd-tag">ç®¡ç†å‘˜</span>{% endif %}</div>
      {% endfor %}
    </div>
    {% endfor %}

    <div class="group">
      <div class="group-h">&#127899;&#65039; å¯é€‰å‚æ•°ï¼ˆè·Ÿåœ¨æç¤ºè¯åï¼Œå‡å¯çœç•¥ï¼‰</div>
      <div class="pgrid">
        {% for p in params %}<div class="pi"><span class="pn">{{ p.name }}</span><span class="pd">{{ p.desc }}</span></div>{% endfor %}
      </div>
    </div>

    <div class="group">
      <div class="group-h">&#128221; ç¤ºä¾‹</div>
      <div class="ex">{% for e in examples %}<div class="ex-l">{{ e }}</div>{% endfor %}</div>
    </div>

    <div class="info">{{ wf_line }}<br/>{{ mode_line }}</div>
  </div>

  <div class="footer">&#128048; Rabbit House ï½œ ä»Šå¤©ä¹Ÿç”»ç‚¹æ¸©æŸ”çš„ä¸œè¥¿å§ã€‚</div>
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
        <div class="logo">ğŸ¨</div>
        <div>
          <div class="title">äº‘ç»˜å›¾å¿«æ·é¢„è®¾</div>
          <div class="subtitle">ä¸€æ¡å‚æ•°ï¼Œå¿«é€Ÿåˆ‡æ¢æˆå“é£æ ¼</div>
        </div>
      </div>
      <div class="badge">GPT-Image Â· æ–‡ç”Ÿå›¾ / å›¾ç”Ÿå›¾</div>
    </div>
    <div class="grid">
      {% for item in items %}
      <div class="preset">
        <div class="preset-top">
          <span class="name">{{ item.icon }} {{ item.name }}</span>
          <span class="flag">--{{ item.name }}</span>
        </div>
        <div class="desc">{{ item.desc }}</div>
        <div class="size">æ¨èå°ºå¯¸ Â· {{ item.size }}</div>
      </div>
      {% endfor %}
    </div>
    <div class="usage">
      <div class="usage-title">âœ¨ ä½¿ç”¨ç¤ºä¾‹</div>
      <div class="example">/äº‘ç»˜å›¾ é“¶å‘å°‘å¥³ï¼Œè“è‰²è¿è¡£è£™ --æ‰‹åŠ</div>
      <div class="example">å¼•ç”¨æˆ–é™„å¸¦åŸå›¾ â†’ /å˜æ‰‹åŠ</div>
      <div class="example">å›å¤åŸå›¾ â†’ /äº‘ç»˜å›¾ --æ¯›ç»’</div>
      <div class="tip">
        é™„å¸¦åŸå›¾æ—¶ä¼šè‡ªåŠ¨åˆ‡æ¢åˆ°äº‘ç«¯å›¾ç‰‡ç¼–è¾‘ï¼Œå°½é‡ä¿ç•™äººç‰©èº«ä»½ã€è„¸éƒ¨ã€æœè£…ã€å§¿åŠ¿ä¸æ„å›¾ï¼›
        é»˜è®¤æ²¿ç”¨ç¬¬ä¸€å¼ åŸå›¾åˆ†è¾¨ç‡ï¼Œæ‰‹åŠ¨å¡«å†™ --size æ—¶ä»¥æŒ‡å®šå°ºå¯¸ä¸ºå‡†ã€‚
      </div>
    </div>
    <div class="footer">Rabbit House Â· äº‘ç«¯ç»˜å›¾ä¼šæ¶ˆè€—å¯¹åº”æ¥å£é¢åº¦</div>
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
      <div class="title">âœ¨ ä»Šæ—¥çš„äºŒæ¬¡å…ƒçš„ä½ </div>
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


class ComfyUIError(Exception):
    """ComfyUI äº¤äº’è¿‡ç¨‹ä¸­çš„å¯è¯»é”™è¯¯ã€‚"""
    pass


class ComfyUIDrawPlugin(Star):
    # æŒ‡ä»¤è¡Œå†…å‚æ•°åˆ«å -> å†…éƒ¨ key
    FLAG_ALIASES = {
        "--neg": "negative", "--no": "negative", "-n": "negative", "--negative": "negative",
        "--size": "size", "-s": "size", "--wh": "size",
        "--steps": "steps", "--step": "steps",
        "--cfg": "cfg",
        "--seed": "seed",
        "--batch": "batch", "-b": "batch", "--count": "batch",
        "--wf": "workflow", "-w": "workflow", "--workflow": "workflow",
        "--lora": "lora", "-l": "lora", "--lo": "lora",
        "--quality": "quality", "-q": "quality",
        "--style": "style",
        "--preset": "preset", "--é¢„è®¾": "preset",
        "--fw": "forward", "--forward": "fç}7ŞÚ$z{-®éÜj×"" ¢FVb'6Uö–çB†¶W’ÂÆ&VÂÂÖ–æ–×VÒÂÖ†–×VÒ“ ¢fÇVRÒ÷WBævWB†¶W’¢–bfÇVR—2æöæR÷"fÇVRÓÒ"# ¢&WGW&à¢G'“ ¢'6VBÒ–çB‡7G"‡fÇVR’ç7G&—‚’¢W†6WB…G—TW'&÷"ÂfÇVTW'&÷"“ ¢&—6R6öÖg•T”W'&÷"†b'¶Æ&VÇÒ[ø^š¾iŠşi[Ni[8""¢–bæ÷BÖ–æ–×VÒÃÒ'6VBÃÒÖ†–×VÓ ¢&—6R6öÖg•T”W'&÷"†b'¶Æ&VÇÒ[ø^š¾YÊ‚¶Ö–æ–×V×ÒX‹¶Ö†–×V×ÒK˜¾™{N8""¢÷WE¶¶W•ÒÒ'6V@ ¢'6Uö–çB€¢&&F6‚"À¢.yIşh‰[Êi["À¢À¢6VÆbåö6öæf–uö–çB‚&Ö…ö&F6…÷6—¦R"ÂBÂÂ’À¢¢–b6Æ÷VC ¢&WGW&â÷W@ ¢'6Uö–çB€¢'7FW2"À¢.˜x~j~jÚ^i["À¢À¢6VÆbåö6öæf–uö–çB‚&Ö…÷7FW2"ÂSÂÂ’À¢¢'6Uö–çB‚'6VVB"Â.zxŞZÙ"ÂÂ"¢¢c2Ò ¢6frÒ÷WBævWB‚&6fr"¢–b6fr—2æ÷BæöæRæB6frÒ"# ¢G'“ ¢6frÒfÆöB‡7G"†6fr’ç7G&—‚’¢W†6WB…G—TW'&÷"ÂfÇVTW'&÷"“ ¢&—6R6öÖg•T”W'&÷"‚$4dr[ø^š¾iŠşi[ZÙ~8""¢Ö…ö6frÒ6VÆbåö6öæf–uöfÆöB‚&Ö…ö6fr"ÂãÂãÂã¢–bæ÷BÖF‚æ—6f–æ—FR†6fr’÷"æ÷BÃÒ6frÃÒÖ…ö6fs ¢&—6R6öÖg•T”W'&÷"†b$4dr[ø^š¾iŠòX‹¶Ö…ö6fs¦wÒK˜¾™{Ny¨NiÈ™™i[ZÙ~8""¢÷WE²&6fr%ÒÒ6fp ¢6—¦RÒ÷WBævWB‚'6—¦R"¢–b6—¦S ¢æ÷&ÖÆ—¦VBÒ7G"‡6—¦R¢f÷"6W–â‚%‚"Â"¢"Â,9r"Â.)ÉR"Â.)Éb"“ ¢æ÷&ÖÆ—¦VBÒæ÷&ÖÆ—¦VBç&WÆ6R‡6WÂ'‚"¢'G2Òæ÷&ÖÆ—¦VBç7Æ—B‚'‚"¢–bÆVâ‡'G2’Ò# ¢&—6R6öÖg•T”W'&÷"‚.[®ZûjÎ[Èş[©NK‹¢Zë×š¹ûÈÎKè¾Zh"sc‡ƒ#N8""¢G'“ ¢v–GF‚Â†V–v‡BÒ–çB‡'G5³Ò’Â–çB‡'G5³Ò¢W†6WBfÇVTW'&÷# ¢&—6R6öÖg•T”W'&÷"‚.[®ZûKŠŞy¨NZëŞY(Îš¹[ø^š¾iŠşi[Ni[8""¢–bæ÷BƒcBÃÒv–GF‚ÃÒ#C‚æBcBÃÒ†V–v‡BÃÒ#C‚“ ¢&—6R6öÖg•T”W'&÷"‚.ZëŞY(Îš¹˜;Ş[ø^š¾YÊ‚cBX‹#C‚K˜¾™{N8""¢÷WE²'6—¦R%ÒÒb'·6VÆbå÷&÷VæC‚‡v–GF‚—×‡·6VÆbå÷&÷VæC‚††V–v‡B—Ò ¢&WGW&â÷W@ ¢FVböVæf÷&6UöVffV7F—fUöÆ–Ö—G2‡6VÆbÂVffV7F—fR“ ¢"".j
š¨ÎiÈ{¸[z^KÙÎkXXø.i[ûÈÎ‹ùî[z^KÙÎkXˆz®[Šny¨Nš¹š8î™šXÎK™ş{«>XZ^KùŞhªN8""" ¢Ö…÷7FW2Ò6VÆbåö6öæf–uö–çB‚&Ö…÷7FW2"ÂSÂÂ¢7FW2ÒVffV7F—fRævWB‚'7FW2"¢–b—6–ç7Fæ6R‡7FW2Â†–çBÂfÆöB’’æBæ÷B—6–ç7Fæ6R‡7FW2Â&ööÂ“ ¢–bæ÷BÖF‚æ—6f–æ—FR†fÆöB‡7FW2’’÷"7FW2Â÷"7FW2âÖ…÷7FW3 ¢&—6R6öÖg•T”W'&÷"†b.[z^KÙÎkXZéî™˜^˜x~j~jÚ^i[‹h^X{®XXŠëˆÈ>Y»B(	7¶Ö…÷7FW7Ş8"" ¢v–GF‚Â†V–v‡BÒVffV7F—fRævWB‚'v–GF‚"’ÂVffV7F—fRævWB‚&†V–v‡B"¢&F6‚ÒVffV7F—fRævWB‚&&F6…÷6—¦R"’÷"¢çVÖW&–2Ò‡v–GF‚Â†V–v‡BÂ&F6‚¢–bÆÂ†—6–ç7Fæ6R‡bÂ†–çBÂfÆöB’’æBæ÷B—6–ç7Fæ6R‡bÂ&ööÂ’f÷"b–âçVÖW&–2“ ¢F÷FÂÒ–çB‡v–GF‚’¢–çB††V–v‡B’¢–çB†&F6‚¢Ö…÷—†VÇ2Ò6VÆbåö6öæf–uö–çB€¢&Ö…÷F÷FÅ÷—†VÇ2"Âƒ3ƒƒc‚Â#c#CBÂ ¢¢–bF÷FÂâÖ…÷—†VÇ3 ¢&—6R6öÖg•T”W'&÷"€¢b.K»¾Xªh¾X8ş{J˜xò·F÷FÃ¢ÇÒ‹h^‹ø~Kˆ®™™¶Ö…÷—†VÇ3¢ÇŞûÉ² ¢.Šû~Xxş[ş[®Zûh‰nyIşh‰[Êi[8" ¢ ¢FVbö6öæf–uö–çB‡6VÆbÂ¶W’ÂFVfVÇBÂÖ–æ–×VÓÔæöæRÂÖ†–×VÓÔæöæR“ ¢G'“ ¢fÇVRÒ–çB‡6VÆbæ6öæf–rævWB†¶W’ÂFVfVÇB’¢W†6WB…G—TW'&÷"ÂfÇVTW'&÷"“ ¢fÇVRÒ–çB†FVfVÇB¢–bÖ–æ–×VÒ—2æ÷BæöæS ¢fÇVRÒÖ‚†Ö–æ–×VÒÂfÇVR¢–bÖ†–×VÒ—2æ÷BæöæS ¢fÇVRÒÖ–â†Ö†–×VÒÂfÇVR¢&WGW&âfÇVP ¢FVbö6öæf–uöfÆöB‡6VÆbÂ¶W’ÂFVfVÇBÂÖ–æ–×VÓÔæöæRÂÖ†–×VÓÔæöæR“ ¢G'“ ¢fÇVRÒfÆöB‡6VÆbæ6öæf–rævWB†¶W’ÂFVfVÇB’¢W†6WB…G—TW'&÷"ÂfÇVTW'&÷"“ ¢fÇVRÒfÆöB†FVfVÇB¢–bæ÷BÖF‚æ—6f–æ—FR‡fÇVR“ ¢fÇVRÒfÆöB†FVfVÇB¢–bÖ–æ–×VÒ—2æ÷BæöæS ¢fÇVRÒÖ‚†Ö–æ–×VÒÂfÇVR¢–bÖ†–×VÒ—2æ÷BæöæS ¢fÇVRÒÖ–â†Ö†–×VÒÂfÇVR¢&WGW&âfÇVP ¢FVböÖ…ö'—FW2‡6VÆbÂ¶W’ÂFVfVÇEöÖ"“ ¢Ö"Ò6VÆbåö6öæf–uö–çB†¶W’ÂFVfVÇEöÖ"ÂÂ#C‚¢&WGW&âÖ"¢#B¢#@ ¢7FF–6ÖWF†ö@¢7–æ2FVb÷&VEöÆ–Ö—FVB‡&W7öç6RÂÆ–Ö—BÂÆ&VÂ“ ¢"".kX[ÈşŠû¾XùnY8Ş[©NûÈÎ˜şXXŞKˆKŠ®[È.[‹Y»îx˜rşŠxnš)ˆ	~[Ş‹ù¾zˆ¾Xh^ZÙ8""" ¢ÆVæwF‚Ò&W7öç6Ræ†VFW'2ævWB‚$6öçFVçBÔÆVæwF‚"¢–bÆVæwFƒ ¢G'“ ¢–b–çB†ÆVæwF‚’âÆ–Ö—C ¢&—6R6öÖg•T”W'&÷"€¢b'¶Æ&VÇŞKÙ>zzş‹h^‹ø~Kˆ®™™ûÈiÈZJr¶Æ–Ö—Bòò#Bòò#GÒÔ.ûÈ8" ¢¢W†6WBfÇVTW'&÷# ¢70¢FFÒ'—FV'&’‚¢7–æ2f÷"6‡Væ²–â&W7öç6Ræ6öçFVçBæ—FW%ö6‡Væ¶VBƒcB¢#B“ ¢FFæW‡FVæB†6‡Væ²¢–bÆVâ†FF’âÆ–Ö—C ¢&—6R6öÖg•T”W'&÷"€¢b'¶Æ&VÇŞKÙ>zzş‹h^‹ø~Kˆ®™™ûÈiÈZJr¶Æ–Ö—Bòò#Bòò#GÒÔ.ûÈ8" ¢¢&WGW&â'—FW2†FF ¢7FF–6ÖWF†ö@¢FVb÷Fõö–çB‡bÂFVfVÇB“ ¢–bb—2æöæS ¢&WGW&âFVfVÇ@¢G'“ ¢&WGW&â–çB‡7G"‡b’ç7G&—‚’¢W†6WBW†6WF–öã ¢&WGW&âFVfVÇ@ ¢7FF–6ÖWF†ö@¢FVb÷FõöfÆöB‡bÂFVfVÇB“ ¢–bb—2æöæS ¢&WGW&âFVfVÇ@¢G'“ ¢&WGW&âfÆöB‡7G"‡b’ç7G&—‚’¢W†6WBW†6WF–öã ¢&WGW&âFVfVÇ@ ¢7FF–6ÖWF†ö@¢FVb÷7G&—ö6öÖÖæB†ÖW76vU÷7G"ÂæÖW2“ ¢"".K¸îkhhşih~iÊÎ˜xÎXš^hèŠznXùhÈ~KºNûÈY
¾Xúşˆ;Şy¨NYJN˜i.X˜Ş{ÈûÈûÈÎ‹ùNY¹îXø.i[˜:Xˆn8""" ¢2Ò†ÖW76vU÷7G"÷"""’ç7G&—‚¢–bæ÷B3 ¢&WGW&â" ¢æÖW2Ò·‚æÆ÷vW"‚’f÷"‚–âæÖW7Ğ¢'G2Ò2ç7Æ—B†Ö‡7Æ—CÓ¢f—'7BÒ'G5³ÒæÇ7G&—‚"ò2î8"ÇTdc2"’æÆ÷vW"‚¢–bf—'7B–âæÖW3 ¢&WGW&â'G5³Òç7G&—‚’–bÆVâ‡'G2’âVÇ6R" ¢&WGW&â0 ¢7FF–6ÖWF†ö@¢FVb÷W6vR‚“ ¢&WGW&â€¢/	øê‚6öÖg•T’{¹Y»åÆâ ¢.yJk9^ûÉ¢ş{¹Y»âÎhùzK®ŠøÓâ¾Xúş˜Xø.i[ÕÆâ ¢.Xúş˜Xø.i[ûÉ¥Æâ ¢"ÒÖæVrÎ‹IşY	ŠøÓâ‹IşY	hùzK®ŠøŞûÈXúşZI®ŠøŞûÈ•Æâ ¢"Ò×6—¦RZë×š¹‚Kè¾Zh"Ò×6—¦Rsc‡ƒS%Æâ ¢"ÒŞjŠ®Y»âòÒŞz¹nY»â[ú¾hÛ~[®ZûûÈXúniÈ’ÒŞikY»âòÒŞZëŞY»âòÒŞZëŞ[şûÈ•Æâ ¢"Ò×7FW2â˜x~j~jÚ^i[Æâ ¢"ÒÖ6frâ4dri[XÅÆâ ¢"Ò×6VVBâY»®Zé®zxŞZÙÆâ ¢"ÒÖ&F6‚âyIşh‰[Êi[Æâ ¢"×rÎ[z^KÙÎkXYÓâ˜hº[z^KÙÎkXûÈŠxş{¹Y»îX‰~ŠûÈ•Æâ ¢"ÒÖÆ÷&YŞz{³®iØ>˜xÕÒK‹Ni{nXªÆõ$ûÈÎXúşZI®jÊûÈÎZh"ÒÖÆ÷&7G–ÆT£ã…Æâ ¢.zK®Kè¾ûÉ¢ş{¹Y»â7WFR6BÂÖ7FW'–V6RÂ&W7BVÆ—G’Ò×6—¦Rsc‡ƒS"Ò×7FW2#UÆâ ¢.ZèÎi[N[ŠîXªûÉ¢ş{¹Y»î[ŠîXª’ ¢ ¢FVbö†VÇ÷FW‡B‡6VÆb“ ¢æÖW2Ò.8"æ¦ö–â‡6VÆbå÷v÷&¶fÆ÷uöæÖW2‚’¢ÖöFRÒ7G"‡6VÆbæ6öæf–rævWB‚'&ö×EöÖöFR"Â'&WVæB"’÷"'&WVæB"’ç7G&—‚’æÆ÷vW"‚¢–bÖöFRæ÷B–â‚'&WVæB"Â&VæB"Â'&WÆ6R"“ ¢ÖöFRÒ'&WVæB ¢ÖöFUöFW62Ò°¢'&WVæB#¢.KÚy¨NŠøŞYÊX˜Ş8[z^KÙÎkXXéşiÈih~iÊÎYÊYîûÈÎKùŞyYŠznXùŠøÒ"À¢&VæB#¢.[z^KÙÎkXXéşiÈih~iÊÎYÊX˜Ş8KÚy¨NŠøŞYÊYâ"À¢'&WÆ6R#¢.yJKÚy¨NŠøŞŠhny¹n[z^KÙÎkXXéşiÈih~iÊÂ"À¢Õ¶ÖöFUĞ¢&WGW&â€¢/	øê‚6öÖg•T’{¹Y»â+rKÛşyJ[ŠîXª•Æâ ¢%Æâ ¢.8	hÈ~KºN8	Æâ ¢"ş{¹Y»âÎhùzK®ŠøÓâ¾Xø.i[ÒX{®Y»îûÈXŠ¾YÒG&rò6öÖg—V’ò6öÖgûÈ•Æâ ¢"şK©{¹Y»âÎhùzK®ŠøÓâ¾Xø.i[ÒK©zºşX{®Y»îûÉ¾iÈXéşY»îi{nˆz®XªY»îx˜~{Én‹éûÈXŠ¾YÒwFG&~ûÈ•Æâ ¢"şXùh˜¾X©â[É^yJ‚ş™˜N[ŠnXéşY»îûÈÎKˆ™Jî‹ÚÎhÚ.h‰h˜¾X©îûÈXŠ¾YÒh˜¾X©îXÉnûÈ•Æâ ¢"şK©{¹Y»îš(NŠëâiú^yÈ¾h˜¾X©î8ZKNX8ş8k[~hª^zØ[ú¾hÛ~š(NŠëåÆâ ¢"şK©{¹Y»îš)Ş[ªbiú^yÈ²6†DuC$’‹JnXû~kš)Ş[ªnûÈ›¹ŠêNK¸^zêynYûÈ•Æâ ¢"ş{¹Y»îX‰~Š‚iú^yÈ¾XúşyJ[z^KÙÎkXûÈXŠ¾YÒG&vÆ—7NûÈ•Æâ ¢"ş{¹Y»îx«nhj8iúR6öÖg•T’iŠşY
nYÊ{«şûÈXŠ¾YÒG&w7FGW>ûÈ•Æâ ¢"ş{¹Y»î›¹ŠêB¾[z^KÙÎkXYÕÒiú^yÈ²òXˆ~hÚ.›¹ŠêN[z^KÙÎkXûÈXŠ¾YÒG&vFVfVÇNûÈ•Æâ ¢"şK¨ÎjÊXX>y¨Nh‰h«ŞXùnK¸®iz^y¨NK¨ÎjÊXX>[	Z[>[Ú.‹ûÈÎjøşK«®jøşZJKˆjÊûÈXŠ¾YÒjøşiz^K¨ÎjÊXX>ûÈ•Æâ ¢"ş{¹Y»î[ŠîXª’i‹îzK®iÊÎ[ŠîXªûÈXŠ¾YÒG&v†VÇûÈ•Æâ ¢%Æâ ¢.8	Xúş˜Xø.i[8	ûÈ˜;ŞXúşyÈyZ^ûÈ•Æâ ¢"ÒÖæVrÎ‹IşY	ŠøÓâ‹IşY	hùzK®ŠøŞûÈÎXúşZI®ŠøŞûÈÎy»NX‹Kˆ¾KˆKŠ®Xø.i[K‹®jÚ%Æâ ¢"Ò×6—¦RZë×š¹‚yIşh‰[®ZûûÈÎZh"Ò×6—¦Rsc‡ƒ#EÆâ ¢"ÒŞjŠ®Y»âòÒŞz¹nY»â[ú¾hÛ~[®ZûûÉ¾XúniÈ’ÒŞikY»âòÒŞZëŞY»âòÒŞZëŞ[õÆâ ¢"Ò×7FW2â˜x~j~jÚ^i[Æâ ¢"ÒÖ6frâ4dri[XÅÆâ ¢"Ò×6VVBâY»®Zé®zxŞZÙûÈÎKëşK¨îZHŞxëûÉ¾KˆŞXiX‰jøşjÊ™¨şiË¥Æâ ¢"ÒÖ&F6‚âKˆjÊyIşh‰[Êi[Æâ ¢"×rÎ[z^KÙÎkXYÓâ˜hºiùZY~[z^KÙÎkXûÈŠxş{¹Y»îX‰~ŠûÈ•Æâ ¢"ÒÖÆ÷&YŞz{³®iØ>˜xÕÒK‹Ni{nXªÆõ$ûÈÎXúşZI®jÊûÈÎZh"ÒÖÆ÷&7G–ÆT£ã…Æâ ¢"Ò×VÆ—G’XÂyIşh‰‹J˜xşûÈK©{¹Y»îûÈÎZh"7FæF&Bò†NûÈ•Æâ ¢"Ò×7G–ÆRXÂyK¾š8îûÈK©{¹Y»îûÈÎZh"f—f–BòæGW&ÎûÈ•Æâ ¢"ÒŞh˜¾X©âòÒŞZKNX8şzØ’K©{¹Y»îhùzK®ŠøŞš(NŠëîûÈXù˜şK©{¹Y»îš(NŠëâiú^yÈ¾XZ˜:ûÈ•Æâ ¢"ÒŞ‹ÚÎXùòÒÖgriÊÎjÊ{¹>iéÎyJY[›n‹ÚÎXùXù˜ûÈK™şXúşYÊ˜XŞ{Úî˜xÎXZ[[ÈY
şûÈ•Æâ ¢%Æâ ¢.8	zK®Kè¾8	Æâ ¢"ş{¹Y»â7WFR6BÂÖ7FW'–V6UÆâ ¢"ş{¹Y»âyK^[ÛhIş[‹rÒŞZëŞ[ò×ršËÎ™(ˆØ’Şiè˜	õÆâ ¢"ş{¹Y»âv—&ÂÂv&FVâÒÖæVrÆ÷w&W2Â&B†æG2Ò×6—¦Rsc‡ƒ#BÒ×7FW2#…Æâ ¢"ş{¹Y»âš8îišòÒ×6VVB#3CR×r[şXûnZÙÆâ ¢.[É^yJKˆ[ÊY»îx˜~YîXù˜şXùh˜¾X©åÆâ ¢.[É^yJKˆ[ÊY»îx˜~YîXù˜şK©{¹Y»âÒŞjù¾{¹%Æâ ¢%Æâ ¢.8	ŠûNiˆî8	Æâ ¢,+rK¸îih~K»nZKXª‹ÛŞy¨N[z^KÙÎkXûÈÎ›¹ŠêNk+şyJX[nˆz®[Šny¨N[®Zû‚òjÚ^i[ò4drò˜x~j~YšzØûÈÎXú®iÈi‹î[ÈşXiK¨nKˆ®™Ú.y¨NXø.i[h˜ŞŠhny¹n8%Æâ ¢b,+rhùzK®ŠøŞKˆî[z^KÙÎkXXéşiÈjÚ>Y	ih~iÊÎy¨NY[›nûÉ®[Ù>X˜ŞK‹¢¶ÖöFWŞûÈ‡¶ÖöFUöFW67ŞûÈûÈÎXúşYÊ˜XŞ{Úâ&ö×EöÖöFR‹>i[N8%Æâ ¢%Æâ ¢b.[Ù>X˜ŞXúşyJ[z^KÙÎkXûÉ§¶æÖW7Ò ¢ ¢2ÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒ0¢2Xù˜òK‹Ni{nih~K»`¢2ÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒ0¢FVböÖVF–ö6ö×öæVçB‡6VÆbÂFF¢'—FW2Âf–ÆVæÖS¢7G"“ ¢W‡BÒ†÷2çF‚ç7Æ—FW‡B†f–ÆVæÖR•³Ò÷""çær"’æÆ÷vW"‚’æÇ7G&—‚"â"¢–bW‡B–â‚&×B"Â'vV&Ò"Â&Ö÷b"“ ¢F‚Ò6VÆbå÷6fU÷FV×†FFÂW‡B¢&WGW&â6ö×åf–FVòæg&öÔf–ÆU7—7FVÒ‡F‚¢2Y»îx˜~ûÉ®KÉXX[	ŞŠù^Xh^ZÙZÙ~ˆ¨.ûÈˆº^Šú^x˜iÊÎiJşhÈûÈûÈÎY
nX‰‰ŞYËK‹®K‹Ni{nih~K»`¢g&öÕö'—FW2ÒvWFGG"„6ö×ä–ÖvRÂ&g&öÔ'—FW2"ÂæöæR¢–b6ÆÆ&ÆR†g&öÕö'—FW2“ ¢G'“ ¢&WGW&âg&öÕö'—FW2†FF¢W†6WBW†6WF–öã¢2æ÷¢$ÄS¢70¢6fUöW‡BÒW‡B–bW‡B–â‚'ær"Â&§r"Â&§Vr"Â'vV'"Â&v–b"’VÇ6R'ær ¢F‚Ò6VÆbå÷6fU÷FV×†FFÂ6fUöW‡B¢&WGW&â6ö×ä–ÖvRæg&öÔf–ÆU7—7FVÒ‡F‚ ¢FVb÷FV×öF—"‡6VÆb“ ¢BÒ÷2çF‚æ¦ö–â‚&FF"Â'FV×"¢G'“ ¢÷2æÖ¶VF—'2†BÂW†—7Eöö³ÕG'VR¢&WGW&â@¢W†6WBW†6WF–öã¢2æ÷¢$ÄS¢BÒ÷2çF‚æ¦ö–â‡FV×f–ÆRævWGFV×F—"‚’Â&7G&&÷Eö6öÖg—V’"¢÷2æÖ¶VF—'2†BÂW†—7Eöö³ÕG'VR¢&WGW&â@ ¢FVb÷6fU÷FV×‡6VÆbÂFF¢'—FW2ÂW‡CÒ'ær"“ ¢F‚Ò÷2çF‚æ¦ö–â‡6VÆbå÷FV×öF—"‚’Âb&6öÖg—V•÷·WV–BçWV–CB‚’æ†W‡Òç¶W‡GÒ"¢v—F‚÷Vâ‡F‚Â'v""’2c ¢bçw&—FR†FF¢&WGW&âF€ ¢FVb÷7vVW÷FV×‡6VÆbÂÖ…övSÓc“ ¢2kˆ^ybXˆn™)şX˜ŞyKiÊÎhù.K»nKª~yIşy¨NK‹Ni{nih~K»nûÈÎ˜şXXŞZnzzşûÉ¾KˆŞXªX‰®yIşh‰y¨NûÈ™‹.jÚ.Y(Î[È.jÚ^Xù˜z¹îK¨ûÈ¢f÷"&6R–â†÷2çF‚æ¦ö–â‚&FF"Â'FV×"’À¢÷2çF‚æ¦ö–â‡FV×f–ÆRævWGFV×F—"‚’Â&7G&&÷Eö6öÖg—V’"’“ ¢G'“ ¢–bæ÷B÷2çF‚æ—6F—"†&6R“ ¢6öçF–çVP¢æ÷rÒF–ÖRçF–ÖR‚¢f÷"fâ–â÷2æÆ—7FF—"†&6R“ ¢–bæ÷Bfâç7F'G7v—F‚‚&6öÖg—V•ò"“ ¢6öçF–çVP¢Ò÷2çF‚æ¦ö–â†&6RÂfâ¢G'“ ¢–bæ÷rÒ÷2çF‚ævWF×F–ÖR‡’âÖ…övS ¢÷2ç&VÖ÷fR‡¢W†6WBW†6WF–öã¢2æ÷¢$ÄS¢70¢W†6WBW†6WF–öã¢2æ÷¢$ÄS¢70 ¢2ÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒ0¢2iØ.š¢2ÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒ0¢7FF–6ÖWF†ö@¢FVb÷7Æ—E÷W&Â‡&r“ ¢"".h¨®yJh‹~Z¾y¨NYËYØŠxNi[Nh‰†‡GGö&6RÂw5ö&6R8.hê^Xù~[Šnh‰nKˆŞ[Šb66†VÖ^8""" ¢&rÒ7G"‡&r’ç7G&—‚¢–b&rç7F'G7v—F‚‚&‡GG¢òò"“ ¢†÷7BÂ66†VÖRÒ&u¶ÆVâ‚&‡GG¢òò"“¥ÒÂ&‡GG ¢VÆ–b&rç7F'G7v—F‚‚&‡GG3¢òò"“ ¢†÷7BÂ66†VÖRÒ&u¶ÆVâ‚&‡GG3¢òò"“¥ÒÂ&‡GG2 ¢VÇ6S ¢†÷7BÂ66†VÖRÒ&rÂ&‡GG ¢†÷7BÒ†÷7Bç7G&—‚"ò"¢w5÷66†VÖRÒ'w72"–b66†VÖRÓÒ&‡GG2"VÇ6R'w2 ¢&WGW&âb'·66†VÖWÓ¢ò÷¶†÷7GÒ"Âb'·w5÷66†VÖWÓ¢ò÷¶†÷7GÒ  ¢FVböf÷&ÖE÷&ö×EöW'&÷"‡6VÆbÂ&öG’“ ¢–b—6–ç7Fæ6R†&öG’ÂF–7B“ ¢W'"Ò&öG’ævWB‚&W'&÷""¢×6rÒ" ¢–b—6–ç7Fæ6R†W'"ÂF–7B“ ¢×6rÒW'"ævWB‚&ÖW76vR"’÷"W'"ævWB‚'G—R"’÷"" ¢VÆ–bW'# ¢×6rÒ7G"†W'"¢W‡G&Ò6VÆbåöf÷&ÖEöæöFUöW'&÷'2†&öG’ævWB‚&æöFUöW'&÷'2"’¢¦ö–æVBÒ†×6r²‚%Æâ"²W‡G&–bW‡G&VÇ6R""’’ç7G&—‚¢&WGW&â¦ö–æVB÷".hùKªN[z^KÙÎkXŠ*²6öÖg•T’h¹.{¹Ş8" ¢&WGW&âb.hùKªN[z^KÙÎkXZK‹J^ûÉ§¶&öG—Ò  ¢7FF–6ÖWF†ö@¢FVböf÷&ÖEöæöFUöW'&÷'2†æöFUöW'&÷'2“ ¢–bæ÷B—6–ç7Fæ6R†æöFUöW'&÷'2ÂF–7B’÷"æ÷BæöFUöW'&÷'3 ¢&WGW&â" ¢'G2ÒµĞ¢f÷"æöFUö–BÂ–æfò–âæöFUöW'&÷'2æ—FV×2‚“ ¢W''2Ò–æfòævWB‚&W'&÷'2"ÂµÒ’–b—6–ç7Fæ6R†–æfòÂF–7B’VÇ6RµĞ¢f÷"R–âW''3 ¢–b—6–ç7Fæ6R†RÂF–7B“ ¢Æ–æRÒb.ˆ¨.x+’¶æöFUö–GÓ¢¶RævWB‚vÖW76vRrÂrr—Ò¶RævWB‚vFWF–Ç2rÂrr—Ò"ç7G&—‚¢'G2æVæB†Æ–æR¢&WGW&â%Æâ"æ¦ö–â‡'G2 ¢7FF–6ÖWF†ö@¢FVböf÷&ÖEöW†V5öW'&÷"†FF“ ¢æöFRÒFFævWB‚&æöFU÷G—R"’÷"FFævWB‚&æöFUö–B"’÷"#ò ¢×6rÒFFævWB‚&W†6WF–öåöÖW76vR"’÷".hš~ŠÎ™IŠúò ¢&WGW&âb.[z^KÙÎkXhš~ŠÎX{®™IûÈˆ¨.x+’¶æöFWŞûÈûÉ§¶×6wÒ 