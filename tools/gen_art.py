"""用插件自己的云绘图接口重新生成 README / 帮助卡片用到的美术图。

用法（在插件根目录）：
    IMAGE_BASE_URL=http://host:port/v1 IMAGE_API_KEY=sk-xxx python tools/gen_art.py [名字 ...]

不带名字时生成 tools/art_prompts.json 里的全部图片；已存在的文件会被覆盖。
示例图的提示词直接取自 presets.py 的云绘图预设，和用户发 /云绘图 xxx --预设 时一致。
只依赖标准库；Key 只从环境变量读取，不要写进仓库。
"""
import base64
import io
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


def shrink(content, out, max_side):
    """缩小并压缩成目标扩展名对应的格式，避免仓库和 README 里塞几 MB 的原图；没有 Pillow 就原样保存。"""
    try:
        from PIL import Image
    except ImportError:
        print("  未安装 Pillow，按原图保存（体积较大）")
        with open(out, "wb") as f:
            f.write(content)
        return
    img = Image.open(io.BytesIO(content))
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    if out.lower().endswith((".jpg", ".jpeg")):
        img.convert("RGB").save(out, "JPEG", quality=86, optimize=True, progressive=True)
    else:
        # 256 色调色板（保留透明度），插画类图标基本看不出差别，体积能小一半以上
        img = img.convert("RGBA").quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.FLOYDSTEINBERG)
        img.save(out, "PNG", optimize=True)


def make_avatar(src, dst, size=320):
    """从帮助插画上半部裁出头像，作为卡片内嵌的小图（JPEG，减小 html_render 的数据量）。"""
    try:
        from PIL import Image
    except ImportError:
        print("  未安装 Pillow，跳过生成卡片小头像")
        return
    with Image.open(src) as img:
        img = img.convert("RGB")
        side = int(min(img.size) * 0.62)
        left, top = (img.width - side) // 2, int(img.height * 0.04)
        img = img.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
        img.save(dst, "JPEG", quality=88)
    print(f"  已生成卡片小头像 {os.path.relpath(dst, ROOT)}")


def make_thumb(src, dst, size=240):
    """把示例图缩成小方图，供 /云绘图预设 卡片内嵌（JPEG，减小 html_render 的数据量）。"""
    try:
        from PIL import Image
    except ImportError:
        print("  未安装 Pillow，跳过生成预设缩略图")
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with Image.open(src) as img:
        img = img.convert("RGB")
        side = min(img.size)
        left, top = (img.width - side) // 2, (img.height - side) // 2
        img = img.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
        img.save(dst, "JPEG", quality=85)
    print(f"  已生成预设缩略图 {os.path.relpath(dst, ROOT)}")


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
        shrink(content, out, item.get("max_side", 1024))
        print(f"  已保存 {item['file']}（{os.path.getsize(out) // 1024} KB）")
        if item["name"] == "help":
            make_avatar(out, os.path.join(ROOT, "assets", "reimu_avatar.jpg"))
        if item.get("thumb"):
            make_thumb(out, os.path.join(ROOT, item["thumb"]))
    if failed:
        sys.exit("以下图片生成失败：" + "、".join(failed))


if __name__ == "__main__":
    main(set(sys.argv[1:]))
