"""指令参数别名、尺寸快捷参数、云绘图提示词预设及「二次元的我」词库。

新增或修改预设只需改这个文件；ComfyUIDrawPlugin 以同名类属性引用这些数据。
"""

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
            "bold clean silhouette, expressive simplified details, saturated harmonious "
            "colors, thick white sticker border, subtle print texture, and a plain clean "
            "background with no unrelated objects. No watermark, logo, signature, or text. "
            "Subject: {subject}"
        ),
    },
    "像素": {
        "size": "1024x1024",
        "desc": "精细复古像素画",
        "prompt": (
            "Recreate the described subject as carefully authored high-detail pixel art. "
            "Use a deliberate limited palette, crisp pixel clusters, readable silhouette, "
            "subtle dithering, game-art lighting, and a coherent pixel-art background. "
            "Keep every edge pixel-sharp with no smooth vector lines. No watermark, logo, "
            "signature, or text. Subject: {subject}"
        ),
    },
    "盲盒": {
        "size": "1024x1024",
        "desc": "高级设计师盲盒玩具",
        "prompt": (
            "Transform the described subject into a premium designer blind-box art toy. "
            "Preserve the subject's signature hairstyle, colors, outfit motifs, and "
            "accessories; use charming stylized proportions, a large expressive head, "
            "compact body, smooth high-quality vinyl, subtle painted details, a small "
            "collector display base, soft studio lighting, and tasteful unbranded display "
            "packaging in the background. Make it clearly a physical designer toy. No "
            "watermark, logo, signature, brand name, or readable text. Subject: {subject}"
        ),
    },
    "水彩": {
        "size": "1024x1536",
        "desc": "通透柔和水彩绘本",
        "prompt": (
            "Reimagine the described subject as a luminous hand-painted watercolor "
            "storybook illustration. Preserve all recognizable features, clothing colors, "
            "pose, and important scene elements; use delicate pigment blooms, transparent "
            "layering, soft wet-on-wet edges, selective crisp details, textured cotton "
            "paper, gentle natural light, and an elegant harmonious palette. Avoid muddy "
            "colors and empty unfinished areas. No watermark, logo, signature, or text. "
            "Subject: {subject}"
        ),
    },
    "赛博": {
        "size": "1024x1536",
        "desc": "电影级赛博霓虹夜景",
        "prompt": (
            "Create a cinematic cyberpunk neon interpretation of the described subject. "
            "Preserve the subject's identity, silhouette, hairstyle, clothing design, and "
            "pose while adding sophisticated futuristic materials, layered city depth, "
            "rain-slick reflections, cyan and magenta practical lights, volumetric haze, "
            "dramatic rim lighting, and premium film color grading. Keep the face clear and "
            "natural rather than oversaturated. No watermark, logo, signature, or text. "
            "Subject: {subject}"
        ),
    },
    "国风": {
        "size": "1024x1536",
        "desc": "雅致新中式工笔水墨",
        "prompt": (
            "Render the described subject as an elegant contemporary Chinese ink-and-color "
            "illustration combining refined gongbi linework with expressive ink washes. "
            "Preserve the subject's recognizable face, hairstyle, outfit colors, pose, and "
            "core composition; use flowing fabric details, restrained mineral pigments, "
            "subtle gold accents, poetic mist, layered mountains or botanical motifs where "
            "appropriate, generous intentional negative space, and fine rice-paper texture. "
            "No calligraphy, seal, watermark, logo, signature, or text. Subject: {subject}"
        ),
    },
    "漫画": {
        "size": "1024x1536",
        "desc": "高对比复古漫画封面",
        "prompt": (
            "Turn the described subject into a polished retro comic-book cover illustration. "
            "Preserve recognizable facial features, hairstyle, clothing, pose, and key scene "
            "elements; use confident ink contours, dynamic perspective, expressive motion, "
            "controlled halftone shading, selective saturated colors, dramatic shadows, and "
            "clean print texture. Compose it like a premium cover but include no title, speech "
            "bubble, watermark, logo, signature, or text. Subject: {subject}"
        ),
    },
    "油画": {
        "size": "1024x1536",
        "desc": "博物馆质感古典油画",
        "prompt": (
            "Paint the described subject as a museum-quality classical oil painting. Preserve "
            "the subject's identity, expression, hairstyle, clothing colors, pose, and major "
            "background forms; use masterful anatomy, layered glazing, subtle impasto, rich "
            "pigment depth, elegant chiaroscuro, soft atmospheric transitions, tactile canvas "
            "texture, and a timeless balanced composition. Keep details refined and faces "
            "natural. No frame, watermark, logo, signature, or text. Subject: {subject}"
        ),
    },
    "手机UI": {
        "size": "1024x1536",
        "desc": "高保真手机 App 界面",
        "prompt": (
            "Design a production-ready high-fidelity mobile app UI for the described product "
            "or scenario. Show one complete vertical application screen directly, not a phone "
            "mockup and not a hand holding a device. Use a clear information hierarchy, an "
            "8-point spacing system, safe-area aware top and bottom navigation, consistent "
            "components, polished icons, accessible contrast, restrained shadows, and a "
            "coherent modern color system. Include concise, correctly spelled, readable UI "
            "labels appropriate to the request; avoid filler text and visual clutter. No "
            "watermark, unrelated logo, presentation board, or device frame. Product brief: {subject}"
        ),
    },
    "网页UI": {
        "size": "1536x1024",
        "desc": "现代响应式网页界面",
        "prompt": (
            "Create a polished production-ready desktop web UI for the described website. "
            "Show the webpage itself at a wide desktop viewport with a purposeful navigation "
            "bar, strong hero or primary workspace, clear content sections, reusable cards, "
            "well-designed controls, and a convincing footer or lower content area when "
            "appropriate. Use a disciplined grid, generous spacing, clear typography, "
            "accessible contrast, subtle depth, and a cohesive design system. Render concise "
            "readable labels instead of gibberish. No browser chrome, laptop mockup, watermark, "
            "unrelated logo, or presentation board. Website brief: {subject}"
        ),
    },
    "后台UI": {
        "size": "1536x1024",
        "desc": "专业 SaaS 后台仪表盘",
        "prompt": (
            "Design a professional high-fidelity SaaS admin dashboard for the described system. "
            "Show a complete desktop interface with a compact sidebar, useful top navigation, "
            "clear page title and filters, KPI summary cards, meaningful charts, a readable data "
            "table, status badges, and practical actions. Use a precise grid, consistent spacing, "
            "accessible colors, restrained shadows, strong data hierarchy, and realistic concise "
            "labels and values. Avoid decorative clutter, tiny unreadable text, fake paragraphs, "
            "browser chrome, device mockups, watermarks, and unrelated logos. System brief: {subject}"
        ),
    },
    "数据大屏": {
        "size": "1536x1024",
        "desc": "科技感数据可视化大屏",
        "prompt": (
            "Create a premium command-center data visualization screen for the described topic. "
            "Use a wide dark interface with a strong central overview, clearly grouped KPI cards, "
            "legible trend charts, maps or topology only when relevant, ranked lists, alerts, and "
            "balanced negative space. Apply a sophisticated restrained luminous palette, crisp "
            "thin-line components, high information density without clutter, and readable concise "
            "labels and numbers. Keep every panel aligned to a coherent grid. No perspective room "
            "mockup, wall display frame, watermark, unrelated logo, or meaningless microtext. "
            "Dashboard brief: {subject}"
        ),
    },
    "电商UI": {
        "size": "1024x1536",
        "desc": "精致移动电商购物界面",
        "prompt": (
            "Design a refined high-conversion mobile e-commerce UI for the described store or "
            "product. Show one complete vertical app screen directly with clear search and "
            "navigation, premium product imagery, concise product information, price and promotion "
            "hierarchy, trustworthy ratings or service benefits, variant controls where relevant, "
            "and an obvious but tasteful purchase action. Use a consistent design system, clean "
            "spacing, readable labels, accessible contrast, and polished commerce components. No "
            "phone frame, hand, presentation board, watermark, unrelated logo, or gibberish text. "
            "Commerce brief: {subject}"
        ),
    },
    "游戏UI": {
        "size": "1536x1024",
        "desc": "沉浸式游戏菜单与 HUD",
        "prompt": (
            "Create a high-fidelity game UI for the described game world and feature. Show the "
            "actual widescreen interface, such as a main menu, inventory, character screen, or "
            "in-game HUD according to the request. Preserve strong environmental art while keeping "
            "all controls, status bars, item slots, navigation, and hierarchy immediately usable. "
            "Use genre-appropriate materials and ornament, consistent iconography, readable concise "
            "labels, clear focus states, and excellent contrast. Avoid excessive decoration over "
            "content, tiny text, device mockups, watermark, unrelated logos, and presentation boards. "
            "Game UI brief: {subject}"
        ),
    },
    "周边目录": {
        "size": "1536x1536",
        "desc": "二次元官方周边贩售图鉴",
        "prompt": (
            "Design a polished square Japanese-anime merchandise catalog and official goods "
            "sales sheet for the described original character or event. Use a large character "
            "hero illustration and decorative event title across the top, plus a compact purchase "
            "bonus panel. Below it, build a precise numbered product grid with two rows and five "
            "columns, showing convincing isolated mockups such as an acrylic stand, badge set, "
            "illustration towel, T-shirt, scarf towel, tote bag, acrylic keychain, wristband, "
            "sticker set, and penlight. Give every product a short readable name and clearly "
            "formatted price. Add tasteful purchase notes and generic payment information in the "
            "footer. Keep the same character identity, costume, logo motif, pastel color system, "
            "lace and star decorations throughout all merchandise. Use the language explicitly "
            "requested in the brief; otherwise use concise readable Chinese. Make the layout "
            "dense but orderly, print-ready, cute, and commercially credible. Do not copy a real "
            "brand, payment logo, or copyrighted event name; no watermark or gibberish microtext. "
            "Catalog brief: {subject}"
        ),
    },
    "联动菜单": {
        "size": "1536x1536",
        "desc": "二次元主题咖啡联动菜单",
        "prompt": (
            "Design a premium square anime collaboration cafe menu for the described original "
            "character, theme, or event. Feature the character and event title in a charming hero "
            "banner, then organize signature drinks, desserts, meals, and set menus into a clean "
            "numbered grid with appetizing product photography or illustrations, short readable "
            "names, ingredients, and clearly formatted prices. Include a compact bonus-gift panel "
            "for coasters or cards, allergy and ordering notes, and a tasteful footer. Maintain a "
            "coherent pastel visual identity across character art, food styling, icons, borders, "
            "and decorative motifs. Use the requested language, otherwise concise readable Chinese. "
            "Keep the page dense but easy to scan, print-ready, cute, and commercially convincing. "
            "Do not use real cafe brands, payment logos, copyrighted event names, watermarks, or "
            "gibberish microtext. Menu brief: {subject}"
        ),
    },
}
CLOUD_PROMPT_PRESET_ALIASES = {
    "变手办": "手办", "figure": "手办", "figurine": "手办",
    "粘土": "黏土", "clay": "黏土",
    "玩偶": "毛绒", "plush": "毛绒",
    "avatar": "头像", "poster": "海报", "wallpaper": "壁纸",
    "sticker": "贴纸", "pixel": "像素", "pixelart": "像素",
    "潮玩": "盲盒", "blindbox": "盲盒", "toy": "盲盒",
    "watercolor": "水彩",
    "霓虹": "赛博", "cyber": "赛博", "cyberpunk": "赛博",
    "水墨": "国风", "工笔": "国风", "ink": "国风",
    "复古漫画": "漫画", "comic": "漫画", "manga": "漫画",
    "oil": "油画", "oilpainting": "油画",
    "手机ui": "手机UI", "appui": "手机UI", "移动ui": "手机UI", "移动端ui": "手机UI",
    "网页ui": "网页UI", "webui": "网页UI", "网页设计": "网页UI", "website": "网页UI",
    "后台ui": "后台UI", "dashboard": "后台UI", "仪表盘": "后台UI", "adminui": "后台UI",
    "大屏": "数据大屏", "dataviz": "数据大屏", "commandcenter": "数据大屏",
    "电商ui": "电商UI", "商城ui": "电商UI", "shopui": "电商UI", "ecommerce": "电商UI",
    "游戏ui": "游戏UI", "gameui": "游戏UI", "hud": "游戏UI",
    "周边ui": "周边目录", "商品目录": "周边目录", "谷子海报": "周边目录",
    "goods": "周边目录", "merch": "周边目录", "merchandise": "周边目录",
    "联动ui": "联动菜单", "菜单ui": "联动菜单", "咖啡菜单": "联动菜单",
    "cafeui": "联动菜单", "collabmenu": "联动菜单",
}
CLOUD_PROMPT_PRESET_FLAGS = {
    "--手办": "手办", "--变手办": "手办", "--figure": "手办",
    "--黏土": "黏土", "--粘土": "黏土", "--clay": "黏土",
    "--毛绒": "毛绒", "--玩偶": "毛绒", "--plush": "毛绒",
    "--头像": "头像", "--avatar": "头像",
    "--海报": "海报", "--poster": "海报",
    "--壁纸": "壁纸", "--wallpaper": "壁纸",
    "--贴纸": "贴纸", "--sticker": "贴纸",
    "--像素": "像素", "--pixel": "像素",
    "--盲盒": "盲盒", "--潮玩": "盲盒", "--blindbox": "盲盒",
    "--水彩": "水彩", "--watercolor": "水彩",
    "--赛博": "赛博", "--霓虹": "赛博", "--cyber": "赛博", "--cyberpunk": "赛博",
    "--国风": "国风", "--水墨": "国风", "--工笔": "国风", "--ink": "国风",
    "--漫画": "漫画", "--复古漫画": "漫画", "--comic": "漫画",
    "--油画": "油画", "--oil": "油画", "--oilpainting": "油画",
    "--手机ui": "手机UI", "--移动ui": "手机UI", "--appui": "手机UI",
    "--网页ui": "网页UI", "--网页设计": "网页UI", "--webui": "网页UI",
    "--后台ui": "后台UI", "--仪表盘": "后台UI", "--dashboard": "后台UI",
    "--数据大屏": "数据大屏", "--大屏": "数据大屏", "--dataviz": "数据大屏",
    "--电商ui": "电商UI", "--商城ui": "电商UI", "--shopui": "电商UI",
    "--游戏ui": "游戏UI", "--gameui": "游戏UI", "--hud": "游戏UI",
    "--周边目录": "周边目录", "--周边ui": "周边目录", "--商品目录": "周边目录",
    "--谷子海报": "周边目录", "--goods": "周边目录", "--merch": "周边目录",
    "--联动菜单": "联动菜单", "--联动ui": "联动菜单", "--菜单ui": "联动菜单",
    "--咖啡菜单": "联动菜单", "--cafeui": "联动菜单", "--collabmenu": "联动菜单",
}
DAILY_ME_NEGATIVE_PROMPT = (
    "worst quality, low quality, lowres, blurry, jpeg artifacts, malformed hands, "
    "extra fingers, missing fingers, text, watermark, logo, signature, artist name, "
    "username, copyright notice, website address, QR code, subtitles"
)


# 「二次元的我」词库：按 用户ID+日期 抽取，增删或调整条目会改变当天已经生成的形象。
DAILY_ME_HAIR_COLORS = [
    ("silver hair", "银发"), ("black hair", "黑发"),
    ("chestnut brown hair", "栗棕发"), ("golden blonde hair", "金发"),
    ("soft pink hair", "柔粉发"), ("deep blue hair", "深蓝发"),
    ("crimson red hair", "绯红发"), ("purple hair", "紫发"),
    ("emerald green hair", "翠绿发"), ("orange hair", "橙发"),
    ("white hair", "白发"), ("light blue hair", "浅蓝发"),
    ("lavender hair", "薰衣草发"), ("mint green hair", "薄荷绿发"),
    ("pink gradient hair", "粉色渐变发"),
    ("blue-to-purple gradient hair", "蓝紫渐变发"),
    ("black hair with red highlights", "黑发红挑染"),
    ("black-to-silver ombre hair", "黑银渐变发"),
]
DAILY_ME_HAIR_STYLES = [
    ("long straight hair", "长直发"), ("short bob cut", "短波波头"),
    ("high twintails", "高双马尾"), ("high ponytail", "高马尾"),
    ("side ponytail", "侧马尾"), ("loose side braid", "侧麻花辫"),
    ("long wavy hair", "长卷发"), ("fluffy short hair", "蓬松短发"),
    ("double hair buns", "双丸子头"), ("soft drill curls", "柔软公主卷"),
    ("hime cut", "姬发式"), ("low twintails", "低双马尾"),
    ("half-up hairstyle", "半扎发"), ("short hair, ahoge", "短发呆毛"),
]
DAILY_ME_EYES = [
    ("ruby red eyes", "红"), ("sapphire blue eyes", "蓝"),
    ("golden eyes", "金"), ("emerald green eyes", "绿"),
    ("amethyst purple eyes", "紫"), ("subtle heterochromia", "异色"),
    ("aqua eyes", "水蓝"), ("rose pink eyes", "粉"),
    ("amber eyes", "琥珀"), ("silver grey eyes", "银灰"),
    ("teal eyes", "青绿"),
]
DAILY_ME_EXPRESSIONS = [
    ("gentle smile", "温柔微笑"), ("bright cheerful smile", "元气笑容"),
    ("calm expression", "清冷沉静"), ("shy smile, light blush", "害羞浅笑"),
    ("confident smile", "自信微笑"), ("sleepy soft gaze", "慵懒睡眼"),
    ("curious expression", "好奇神情"), ("small playful pout", "俏皮轻嘟嘴"),
    ("laughing, closed eyes", "闭眼欢笑"), ("playful grin", "灵动坏笑"),
    ("soft wink", "俏皮眨眼"), ("serene expression", "安静治愈"),
]
# 服装、配饰、场景和光线采用协调套装，避免完全随机产生割裂组合。
DAILY_ME_THEMES = [
    ("校园晨光", "海军蓝制服与红色发带", "在靠窗教室抱着笔记本",
     "navy school blazer, pleated skirt, red hair ribbon, holding a notebook, classroom by the window, soft morning sunlight"),
    ("午后咖啡", "奶油色针织衫与贝雷帽", "在咖啡馆捧着热饮",
     "cream knit sweater, plaid skirt, beret, holding a warm drink, cozy cafe interior, warm window light"),
    ("神社初愿", "红白巫女服与花朵发饰", "站在鸟居前拿着御守",
     "red and white miko outfit, flower hair ornament, holding an omamori charm, Shinto shrine, torii gate, dappled sunlight"),
    ("夏夜祭典", "花纹浴衣与狐狸面具", "在灯笼下拿着团扇",
     "floral yukata, obi, fox mask worn on side of head, holding a folding fan, summer festival, glowing lanterns, warm night lighting"),
    ("霓虹夜行", "黑色短外套与挂脖耳机", "漫步在雨后的霓虹街道",
     "black cropped jacket, casual streetwear, headphones around neck, neon city street after rain, colorful reflections, cinematic rim light"),
    ("海风黄昏", "白色夏日连衣裙与草帽", "站在落日海边迎着微风",
     "flowing white summer dress, straw hat, seaside at sunset, gentle ocean breeze, golden hour backlight"),
    ("静谧书页", "学院风开衫与圆框眼镜", "在图书馆翻阅一本书",
     "academy cardigan, ribbon tie, round glasses, reading an open book, quiet library, soft ambient light"),
    ("星空天台", "深蓝连帽衫与星星发夹", "在天台仰望星空",
     "navy hoodie, star hairpin, rooftop under a starry sky, looking up at the stars, moonlight, subtle city bokeh"),
    ("冬日暖意", "高领毛衣、呢大衣与围巾", "站在飘雪的小镇街角",
     "turtleneck sweater, wool coat, warm scarf, snowy town street, gentle snowfall, warm shop lights"),
    ("玻璃花房", "薄荷色连衣裙与蝴蝶发饰", "在温室花草间轻触花瓣",
     "mint green dress, butterfly hair ornament, touching flower petals, botanical greenhouse, sunbeams through glass, lush plants"),
    ("深海蓝境", "水手领连衣裙与珍珠发夹", "在水族馆玻璃前看游鱼",
     "sailor-collar dress, pearl hairpin, standing before a large aquarium window, glowing fish, blue caustic light"),
    ("月夜魔法", "精致魔女裙与宽檐魔女帽", "在月光花园捧着魔法光球",
     "elegant witch dress, wide-brimmed witch hat, holding a glowing magic orb, moonlit fantasy garden, floating light particles"),
    ("闪耀舞台", "星光偶像服与小皇冠发饰", "在舞台灯光下挥手",
     "sparkling idol costume, small crown hair ornament, waving on stage, colorful spotlights, glittering confetti"),
    ("灯火长街", "改良旗袍与流苏发簪", "走在红灯笼点亮的古街",
     "elegant modern qipao, tassel hairpin, walking along an old street with red lanterns, warm cinematic lighting"),
    ("枫色物语", "棕色针织开衫与格纹围巾", "坐在铺满枫叶的公园长椅",
     "brown knit cardigan, plaid scarf, sitting on a park bench, autumn maple leaves, soft golden light"),
    ("雨声漫步", "浅色风衣与透明雨伞", "走过细雨中的街道",
     "light trench coat, holding a transparent umbrella, rainy street, soft reflections, diffused overcast light"),
    ("深夜便利店", "宽松连帽衫与斜挎小包", "站在便利店灯牌旁喝汽水",
     "oversized hoodie, small crossbody bag, holding a soda bottle, convenience store at night, fluorescent glow, urban bokeh"),
    ("蔷薇庭院", "哥特洛丽塔裙与黑色颈带", "站在盛开的蔷薇拱门下",
     "gothic lolita dress, black choker, rose garden archway, drifting petals, dramatic soft light"),
]


# /云绘图预设 卡片上每个预设的图标。
CLOUD_PRESET_ICONS = {
    "手办": "🏆", "黏土": "🧸", "毛绒": "🐰", "头像": "👤",
    "海报": "🎬", "壁纸": "🌌", "贴纸": "✨", "像素": "👾",
    "盲盒": "🎁", "水彩": "🖌️", "赛博": "🌃", "国风": "🏮",
    "漫画": "💥", "油画": "🖼️",
    "手机UI": "📱", "网页UI": "🖥️", "后台UI": "📊",
    "数据大屏": "🌐", "电商UI": "🛍️", "游戏UI": "🎮",
    "周边目录": "🎀", "联动菜单": "🍰",
}
