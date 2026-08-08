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
      <div class="badge">GPT-Image · 文生图 / 图生图</div>
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


class ComfyUIError(Exception):
    """ComfyUI 交互过程中的可读错误。"""
    pass


class ComfyUIDrawPlugin(Star):
    # 指令行内参数别名 -> 内部 key
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
        "--preset": "preset", "--预设": "preset",
        "--fw": "forward", "--forward": "forward", "--转发": "forward",
    }
    SIZE_PRESETS = {
        "--横图": "1216x832",
        "--landscape": "1216x832",
        "--竖图": "832x1216",
        "--portrait": "832x1216",
        "--方图": "1024x1024",
        "--square": "1024x1024",
        "--宽图": "1344x768",
        "--宽屏": "1344x768",
        "--wide": "1344x768",
    }
    CLOUD_SIZE_PRESETS = {
        "--横图": "1536x1024",
        "--landscape": "1536x1024",
        "--竖图": "1024x1536",
        "--portrait": "1024x1536",
        "--方图": "1024x1024",
        "--square": "1024x1024",
        "--宽图": "1536x1024",
        "--宽屏": "1536x1024",
        "--wide": "1536x1024",
    }
    CLOUD_PROMPT_PRESETS = {
        "手办": {
            "size": "1024x1024",
            "desc": "收藏级 PVC 手办产品照",
            "prompt": (
                "Turn the described subject into a premium 1/7-scale PVC collectible "
                "figure. Preserve the subject's recognizable appearance, hairstyle, "
                "clothing, colors, accessories, and personality. Show the complete "
                "manufactured figurine standing on a tasteful display base, with realistic "
                "painted plastic and resin materials, fine sculpted details, professional "
                "studio product photography, softbox lighting, shallow depth of field, and "
                "an elegant collector-box backdrop. Make it clearly a physical figurine, "
                "not a real person. No watermark, logo, signature, or extra text. Subject: {subject}"
            ),
        },
        "黏土": {
            "size": "1024x1024",
            "desc": "可爱 Q 版黏土人",
            "prompt": (
                "Reimagine the described subject as a cute handmade chibi polymer-clay "
                "figurine. Preserve the key identity, colors, outfit, and accessories; use "
                "a large expressive head, small body, visible handcrafted clay texture, "
                "rounded forms, miniature diorama base, warm tabletop lighting, and crisp "
                "macro photography. No watermark, logo, signature, or text. Subject: {subject}"
            ),
        },
        "毛绒": {
            "size": "1024x1024",
            "desc": "柔软可爱的毛绒玩偶",
            "prompt": (
                "Transform the described subject into an adorable premium plush toy. "
                "Preserve recognizable colors, hairstyle, clothing motifs, and accessories; "
                "use soft short-pile fabric, embroidered facial features, neat stitching, "
                "rounded huggable proportions, cozy product photography, warm diffused "
                "lighting, and a clean background. No watermark, logo, signature, or text. "
                "Subject: {subject}"
            ),
        },
        "头像": {
            "size": "1024x1024",
            "desc": "精致社交头像",
            "prompt": (
                "Create a polished square profile avatar of the described subject. Use a "
                "centered head-and-shoulders composition, a clear expressive face, flattering "
                "soft lighting, refined detail, harmonious colors, a simple layered background, "
                "and strong readability at small size. No frame, watermark, logo, signature, "
                "or text. Subject: {subject}"
            ),
        },
        "海报": {
            "size": "1024x1536",
            "desc": "竖版电影感宣传海报",
            "prompt": (
                "Design a premium vertical cinematic promotional poster featuring the "
                "described subject. Use a striking focal composition, dramatic lighting, "
                "layered depth, atmospheric background elements, strong color grading, and "
                "clean intentional negative space for an optional title. Do not invent words; "
                "include no watermark, logo, signature, or text unless the subject description "
                "explicitly requests exact wording. Subject: {subject}"
            ),
        },
        "壁纸": {
            "size": "1536x1024",
            "desc": "横版电影感桌面壁纸",
            "prompt": (
                "Create a cinematic widescreen desktop wallpaper of the described subject. "
                "Use a spacious landscape composition, place the main subject slightly off "
                "center, add rich environmental storytelling, layered depth, detailed lighting, "
                "and balanced areas that remain visually calm behind desktop icons. No border, "
                "watermark, logo, signature, or text. Subject: {subject}"
            ),
        },
        "贴纸": {
            "size": "1024x1024",
            "desc": "粗描边模切贴纸",
            "prompt": (
                "Turn the described subject into a cute die-cut sticker illustration. Use a "
                "bold clean silhouette, expressive sim…37275 tokens truncated…de.get("inputs", {}) or {}).get("model")
        if not (isinstance(ref, list) and ref):
            return None
        cur_id, slot = str(ref[0]), (ref[1] if len(ref) > 1 else 0)
        visited = set()
        for _ in range(max_hop):
            cur = workflow.get(cur_id)
            if not isinstance(cur, dict):
                return [cur_id, slot]
            cls = str(cur.get("class_type", ""))
            if "lora" in cls.lower():
                mref = (cur.get("inputs", {}) or {}).get("model")
                if isinstance(mref, list) and mref and cur_id not in visited:
                    visited.add(cur_id)
                    cur_id, slot = str(mref[0]), (mref[1] if len(mref) > 1 else 0)
                    continue
                return [cur_id, slot]
            return [cur_id, slot]
        return [cur_id, slot]

    @staticmethod
    def _max_int_id(workflow):
        mx = 0
        for k in workflow.keys():
            try:
                mx = max(mx, int(str(k)))
            except Exception:  # noqa: BLE001
                pass
        return max(mx, 1000)

    # ------------------------------------------------------------------ #
    # 参数解析
    # ------------------------------------------------------------------ #
    def _parse_args(self, text: str, cloud: bool = False):
        tokens = text.split()
        opts = {
            "negative": None, "size": None, "steps": None,
            "cfg": None, "seed": None, "batch": None, "workflow": None,
            "quality": None, "style": None, "preset": None, "forward": None,
            "loras": [],
        }
        size_presets = self.CLOUD_SIZE_PRESETS if cloud else self.SIZE_PRESETS
        positive = []
        i, n = 0, len(tokens)
        while i < n:
            tok = tokens[i]
            prompt_preset = (
                self.CLOUD_PROMPT_PRESET_FLAGS.get(tok.lower()) if cloud else None
            )
            if prompt_preset:
                opts["preset"] = prompt_preset
                i += 1
                continue
            preset_size = size_presets.get(tok.lower())
            if preset_size:
                opts["size"] = preset_size
                i += 1
                continue
            key = self.FLAG_ALIASES.get(tok.lower())
            if key == "forward":
                # 布尔开关：不吃后面的值
                opts["forward"] = "1"
                i += 1
                continue
            if key == "negative":
                # 负向词收集到下一个 flag 为止（可多词）
                i += 1
                vals = []
                while (
                    i < n
                    and tokens[i].lower() not in self.FLAG_ALIASES
                    and tokens[i].lower() not in size_presets
                    and (
                        not cloud
                        or tokens[i].lower() not in self.CLOUD_PROMPT_PRESET_FLAGS
                    )
                ):
                    vals.append(tokens[i])
                    i += 1
                opts["negative"] = " ".join(vals).strip()
                continue
            elif key == "lora":
                # 可重复：--lora 名称[:权重]，每次取一个 token
                if i + 1 < n:
                    opts["loras"].append(tokens[i + 1])
                    i += 2
                else:
                    i += 1
                continue
            elif key:
                if i + 1 < n:
                    opts[key] = tokens[i + 1]
                    i += 2
                else:
                    i += 1
                continue
            else:
                positive.append(tok)
                i += 1
        return " ".join(positive).strip(), opts

    def _resolve_size(self, size_str):
        dw = self._config_int("default_width", 512, 64, 2048)
        dh = self._config_int("default_height", 512, 64, 2048)
        if size_str:
            for sep in ("x", "X", "*", "×", "✕", "✖"):
                if sep in size_str:
                    a, _, b = size_str.partition(sep)
                    try:
                        return self._clamp_dim(int(a)), self._clamp_dim(int(b))
                    except Exception:
                        break
        return self._round8(dw), self._round8(dh)

    def _clamp_dim(self, v):
        return self._round8(max(64, min(2048, int(v))))

    @staticmethod
    def _round8(v):
        return int(round(int(v) / 8) * 8)

    def _clamp_batch(self, v):
        mx = self._config_int("max_batch_size", 4, 1, 100)
        return max(1, min(mx, int(v)))

    def _normalize_options(self, prompt, opts, cloud=False):
        """严格校验用户可控参数，避免无效值或超大任务直接进入后端。"""
        out = dict(opts or {})
        max_prompt = self._config_int("max_prompt_length", 4000, 100, 100000)
        if len(str(prompt or "")) > max_prompt:
            raise ComfyUIError(f"提示词过长，最多允许 {max_prompt} 个字符。")

        def parse_int(key, label, minimum, maximum):
            value = out.get(key)
            if value is None or value == "":
                return
            try:
                parsed = int(str(value).strip())
            except (TypeError, ValueError):
                raise ComfyUIError(f"{label} 必须是整数。")
            if not minimum <= parsed <= maximum:
                raise ComfyUIError(f"{label} 必须在 {minimum} 到 {maximum} 之间。")
            out[key] = parsed

        parse_int(
            "batch",
            "生成张数",
            1,
            self._config_int("max_batch_size", 4, 1, 100),
        )
        if cloud:
            return out

        parse_int(
            "steps",
            "采样步数",
            1,
            self._config_int("max_steps", 150, 1, 10000),
        )
        parse_int("seed", "种子", 0, 2 ** 63 - 1)

        cfg = out.get("cfg")
        if cfg is not None and cfg != "":
            try:
                cfg = float(str(cfg).strip())
            except (TypeError, ValueError):
                raise ComfyUIError("CFG 必须是数字。")
            max_cfg = self._config_float("max_cfg", 100.0, 0.1, 1000.0)
            if not math.isfinite(cfg) or not 0 <= cfg <= max_cfg:
                raise ComfyUIError(f"CFG 必须是 0 到 {max_cfg:g} 之间的有限数字。")
            out["cfg"] = cfg

        size = out.get("size")
        if size:
            normalized = str(size)
            for sep in ("X", "*", "×", "✕", "✖"):
                normalized = normalized.replace(sep, "x")
            parts = normalized.split("x")
            if len(parts) != 2:
                raise ComfyUIError("尺寸格式应为 宽x高，例如 768x1024。")
            try:
                width, height = int(parts[0]), int(parts[1])
            except ValueError:
                raise ComfyUIError("尺寸中的宽和高必须是整数。")
            if not (64 <= width <= 2048 and 64 <= height <= 2048):
                raise ComfyUIError("宽和高都必须在 64 到 2048 之间。")
            out["size"] = f"{self._round8(width)}x{self._round8(height)}"
        return out

    def _enforce_effective_limits(self, effective):
        """校验最终工作流参数，连工作流自带的高风险值也纳入保护。"""
        max_steps = self._config_int("max_steps", 150, 1, 10000)
        steps = effective.get("steps")
        if isinstance(steps, (int, float)) and not isinstance(steps, bool):
            if not math.isfinite(float(steps)) or steps < 1 or steps > max_steps:
                raise ComfyUIError(f"工作流实际采样步数超出允许范围 1–{max_steps}。")

        width, height = effective.get("width"), effective.get("height")
        batch = effective.get("batch_size") or 1
        numeric = (width, height, batch)
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in numeric):
            total = int(width) * int(height) * int(batch)
            max_pixels = self._config_int(
                "max_total_pixels", 8388608, 262144, 1000000000
            )
            if total > max_pixels:
                raise ComfyUIError(
                    f"任务总像素量 {total:,} 超过上限 {max_pixels:,}；"
                    "请减小尺寸或生成张数。"
                )

    def _config_int(self, key, default, minimum=None, maximum=None):
        try:
            value = int(self.config.get(key, default))
        except (TypeError, ValueError):
            value = int(default)
        if minimum is not None:
            value = max(minimum, value)
        if maximum is not None:
            value = min(maximum, value)
        return value

    def _config_float(self, key, default, minimum=None, maximum=None):
        try:
            value = float(self.config.get(key, default))
        except (TypeError, ValueError):
            value = float(default)
        if not math.isfinite(value):
            value = float(default)
        if minimum is not None:
            value = max(minimum, value)
        if maximum is not None:
            value = min(maximum, value)
        return value

    def _max_bytes(self, key, default_mb):
        mb = self._config_int(key, default_mb, 1, 2048)
        return mb * 1024 * 1024

    @staticmethod
    async def _read_limited(response, limit, label):
        """流式读取响应，避免一个异常图片/视频耗尽进程内存。"""
        length = response.headers.get("Content-Length")
        if length:
            try:
                if int(length) > limit:
                    raise ComfyUIError(
                        f"{label}体积超过上限（最大 {limit // 1024 // 1024} MB）。"
                    )
            except ValueError:
                pass
        data = bytearray()
        async for chunk in response.content.iter_chunked(64 * 1024):
            data.extend(chunk)
            if len(data) > limit:
                raise ComfyUIError(
                    f"{label}体积超过上限（最大 {limit // 1024 // 1024} MB）。"
                )
        return bytes(data)

    @staticmethod
    def _to_int(v, default):
        if v is None:
            return default
        try:
            return int(str(v).strip())
        except Exception:
            return default

    @staticmethod
    def _to_float(v, default):
        if v is None:
            return default
        try:
            return float(str(v).strip())
        except Exception:
            return default

    @staticmethod
    def _strip_command(message_str, names):
        """从消息文本里剥掉触发指令（含可能的唤醒前缀），返回参数部分。"""
        s = (message_str or "").strip()
        if not s:
            return ""
        names = {x.lower() for x in names}
        parts = s.split(maxsplit=1)
        first = parts[0].lstrip("/!#.。!\uFF03").lower()
        if first in names:
            return parts[1].strip() if len(parts) > 1 else ""
        return s

    @staticmethod
    def _usage():
        return (
            "🎨 ComfyUI 绘图\n"
            "用法：/绘图 <提示词> [可选参数]\n"
            "可选参数：\n"
            "  --neg <负向词>     负向提示词（可多词）\n"
            "  --size 宽x高       例如 --size 768x512\n"
            "  --横图/--竖图      快捷尺寸（另有 --方图 / --宽图 / --宽屏）\n"
            "  --steps N          采样步数\n"
            "  --cfg N            CFG 数值\n"
            "  --seed N           固定种子\n"
            "  --batch N          生成张数\n"
            "  -w <工作流名>      选择工作流（见 /绘图列表）\n"
            "  --lora 名称[:权重]  临时加 LoRA，可多次，如 --lora styleA:0.8\n"
            "示例：/绘图 a cute cat, masterpiece, best quality --size 768x512 --steps 25\n"
            "完整帮助：/绘图帮助"
        )

    def _help_text(self):
        names = "、".join(self._workflow_names())
        mode = str(self.config.get("prompt_mode", "prepend") or "prepend").strip().lower()
        if mode not in ("prepend", "append", "replace"):
            mode = "prepend"
        mode_desc = {
            "prepend": "你的词在前、工作流原有文本在后，保留触发词",
            "append": "工作流原有文本在前、你的词在后",
            "replace": "用你的词覆盖工作流原有文本",
        }[mode]
        return (
            "🎨 ComfyUI 绘图 · 使用帮助\n"
            "\n"
            "【指令】\n"
            "/绘图 <提示词> [参数]   出图（别名 draw / comfyui / comfy）\n"
            "/云绘图 <提示词> [参数]  云端出图；有原图时自动图片编辑（别名 gptdraw）\n"
            "/变手办                 引用/附带原图，一键转换成手办（别名 手办化）\n"
            "/云绘图预设             查看手办、头像、海报等快捷预设\n"
            "/云绘图额度             查看 ChatGPT2API 账号池额度（默认仅管理员）\n"
            "/绘图列表              查看可用工作流（别名 drawlist）\n"
            "/绘图状态              检查 ComfyUI 是否在线（别名 drawstatus）\n"
            "/绘图默认 [工作流名]    查看 / 切换默认工作流（别名 drawdefault）\n"
            "/二次元的我          抽取今日的二次元少女形象，每人每天一次（别名 每日二次元）\n"
            "/绘图帮助              显示本帮助（别名 drawhelp）\n"
            "\n"
            "【可选参数】（都可省略）\n"
            "--neg <负向词>   负向提示词，可多词，直到下一个参数为止\n"
            "--size 宽x高     生成尺寸，如 --size 768x1024\n"
            "--横图 / --竖图  快捷尺寸；另有 --方图 / --宽图 / --宽屏\n"
            "--steps N        采样步数\n"
            "--cfg N          CFG 数值\n"
            "--seed N         固定种子，便于复现；不写则每次随机\n"
            "--batch N        一次生成张数\n"
            "-w <工作流名>    选择某套工作流（见 /绘图列表）\n"
            "--lora 名称[:权重]  临时加 LoRA，可多次，如 --lora styleA:0.8\n"
            "--quality 值     生成质量（云绘图，如 standard / hd）\n"
            "--style 值       画风（云绘图，如 vivid / natural）\n"
            "--手办/--头像等  云绘图提示词预设（发送 /云绘图预设 查看全部）\n"
            "--转发 / --fw    本次结果用合并转发发送（也可在配置里全局开启）\n"
            "\n"
            "【示例】\n"
            "/绘图 a cute cat, masterpiece\n"
            "/绘图 电影感山谷 --宽屏 -w 鬼针草-极速\n"
            "/绘图 1girl, garden --neg lowres, bad hands --size 768x1024 --steps 28\n"
            "/绘图 风景 --seed 12345 -w 小叶子\n"
            "引用一张图片后发送 /变手办\n"
            "引用一张图片后发送 /云绘图 --毛绒\n"
            "\n"
            "【说明】\n"
            "· 从文件夹加载的工作流，默认沿用其自带的尺寸 / 步数 / CFG / 采样器等，只有显式写了上面的参数才覆盖。\n"
            f"· 提示词与工作流原有正向文本的合并：当前为 {mode}（{mode_desc}），可在配置 prompt_mode 调整。\n"
            "\n"
            f"当前可用工作流：{names}"
        )

    # ------------------------------------------------------------------ #
    # 发送 / 临时文件
    # ------------------------------------------------------------------ #
    def _media_component(self, data: bytes, filename: str):
        ext = (os.path.splitext(filename)[1] or ".png").lower().lstrip(".")
        if ext in ("mp4", "webm", "mov"):
            path = self._save_temp(data, ext)
            return Comp.Video.fromFileSystem(path)
        # 图片：优先尝试内存字节（若该版本支持），否则落地为临时文件
        from_bytes = getattr(Comp.Image, "fromBytes", None)
        if callable(from_bytes):
            try:
                return from_bytes(data)
            except Exception:  # noqa: BLE001
                pass
        safe_ext = ext if ext in ("png", "jpg", "jpeg", "webp", "gif") else "png"
        path = self._save_temp(data, safe_ext)
        return Comp.Image.fromFileSystem(path)

    def _temp_dir(self):
        d = os.path.join("data", "temp")
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except Exception:  # noqa: BLE001
            d = os.path.join(tempfile.gettempdir(), "astrbot_comfyui")
            os.makedirs(d, exist_ok=True)
            return d

    def _save_temp(self, data: bytes, ext="png"):
        path = os.path.join(self._temp_dir(), f"comfyui_{uuid.uuid4().hex}.{ext}")
        with open(path, "wb") as f:
            f.write(data)
        return path

    def _sweep_temp(self, max_age=600):
        # 清理 10 分钟前由本插件产生的临时文件，避免堆积；不动刚生成的（防止和异步发送竞争）
        for base in (os.path.join("data", "temp"),
                     os.path.join(tempfile.gettempdir(), "astrbot_comfyui")):
            try:
                if not os.path.isdir(base):
                    continue
                now = time.time()
                for fn in os.listdir(base):
                    if not fn.startswith("comfyui_"):
                        continue
                    p = os.path.join(base, fn)
                    try:
                        if now - os.path.getmtime(p) > max_age:
                            os.remove(p)
                    except Exception:  # noqa: BLE001
                        pass
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------ #
    # 杂项
    # ------------------------------------------------------------------ #
    @staticmethod
    def _split_url(raw):
        """把用户填的地址规整成 (http_base, ws_base)。接受带或不带 scheme。"""
        raw = str(raw).strip()
        if raw.startswith("http://"):
            host, scheme = raw[len("http://"):], "http"
        elif raw.startswith("https://"):
            host, scheme = raw[len("https://"):], "https"
        else:
            host, scheme = raw, "http"
        host = host.strip("/")
        ws_scheme = "wss" if scheme == "https" else "ws"
        return f"{scheme}://{host}", f"{ws_scheme}://{host}"

    def _format_prompt_error(self, body):
        if isinstance(body, dict):
            err = body.get("error")
            msg = ""
            if isinstance(err, dict):
                msg = err.get("message") or err.get("type") or ""
            elif err:
                msg = str(err)
            extra = self._format_node_errors(body.get("node_errors"))
            joined = (msg + ("\n" + extra if extra else "")).strip()
            return joined or "提交工作流被 ComfyUI 拒绝。"
        return f"提交工作流失败：{body}"

    @staticmethod
    def _format_node_errors(node_errors):
        if not isinstance(node_errors, dict) or not node_errors:
            return ""
        parts = []
        for node_id, info in node_errors.items():
            errs = info.get("errors", []) if isinstance(info, dict) else []
            for e in errs:
                if isinstance(e, dict):
                    line = f"节点 {node_id}: {e.get('message', '')} {e.get('details', '')}".strip()
                    parts.append(line)
        return "\n".join(parts)

    @staticmethod
    def _format_exec_error(data):
        node = data.get("node_type") or data.get("node_id") or "?"
        msg = data.get("exception_message") or "执行错误"
        return f"工作流执行出错（节点 {node}）：{msg}"

