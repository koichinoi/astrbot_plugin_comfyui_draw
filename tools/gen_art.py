"""用插件自己的云绘图接口重新生成 README / 帮助卡片用到的美术图。

用法（在插件根目录）：
    IMAGE_BASE_URL=http://host:port/v1 IMAGE_API_KEY=sk-xxx python tools/gen_art.py [名字 ...]

不带名字时生成 tools/art_prompts.json 里的全部图片；已存在的文件会被覆盖。
示例图的提示词直接取自 presets.py 的云绘图预设，和用户发 /云绘图 xxx --预设 时一致。
只依赖标准库；Key 只从环境变量读取，不要写进仓库。
"""
import base64
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from presets import CLOUD_PROMPT_PRESETS  # noqa: E402


def build_prompt(item, spec):
    if item.get("preset"):
        template = CLOUD_PROMPT_PRESETS[item["preset"]]["prompt"]
        return template.replace("{subject}", spec["subject"])
    prompt = item["prompt"].replace("{subject}", spec["subject"])
    if item.get("default_style"):
        prompt += f"\n画风要求：{spec['default_style']}"
    return prompt


def generate(base, key, model, size, prompt):
    body = json.dumps({"model": model, "prompt": prompt, "size": size, "n": 1}).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/images/generations", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=350) as resp:
        data = json.loads(resp.read())["data"][0]
    if data.get("b64_json"):
        return base64.b64decode(data["b64_json"])
    with urllib.request.urlopen(data["url"], timeout=120) as resp:
        return resp.read()


def make_avatar(src, dst, size=320):
    """把帮助插画缩成卡片内嵌的小头像（JPEG，减小 html_render 的数据量）；没有 Pillow 就跳过。"""
    try:
        from PIL import Image
    except ImportError:
        print("  未安装 Pillow，跳过生成卡片小头像")
        return
    with Image.open(src) as img:
        img = img.convert("RGB")
        side = min(img.size)
        left, top = (img.width - side) // 2, (img.height - side) // 2
        img = img.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
        img.save(dst, "JPEG", quality=88)
    print(f"  已生成卡片小头像 {os.path.relpath(dst, ROOT)}")


def main(names):
    base = os.environ.get("IMAGE_BASE_URL", "").strip()
    key = os.environ.get("IMAGE_API_KEY", "").strip()
    if not base or not key:
        sys.exit("请先设置环境变量 IMAGE_BASE_URL 和 IMAGE_API_KEY")
    with open(os.path.join(ROOT, "tools", "art_prompts.json"), encoding="utf-8") as f:
        spec = json.load(f)
    model = os.environ.get("IMAGE_MODEL", spec["model"])
    failed = []
    for item in spec["images"]:
        if names and item["name"] not in names:
            continue
        out = os.path.join(ROOT, item["file"])
        print(f"→ {item['name']} ({item['size']}) …", flush=True)
        try:
            content = generate(base, key, model, item["size"], build_prompt(item, spec))
        except Exception as e:  # noqa: BLE001
            print(f"  失败：{e}")
            failed.append(item["name"])
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(content)
        print(f"  已保存 {item['file']}（{len(content) // 1024} KB）")
        if item["name"] == "help":
            make_avatar(out, os.path.join(ROOT, "assets", "reimu_avatar.jpg"))
    if failed:
        sys.exit("以下图片生成失败：" + "、".join(failed))


if __name__ == "__main__":
    main(set(sys.argv[1:]))
