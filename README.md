<p align="center">
  <img src="assets/banner.jpg" alt="博丽神社 · ComfyUI 绘图" width="100%">
</p>

<h1 align="center">
  <img src="logo.png" alt="" width="64" align="center"><br>
  astrbot_plugin_comfyui_draw
</h1>

<p align="center">
  <b>博丽神社的画室</b> ── 让 <a href="https://github.com/AstrBotDevs/AstrBot">AstrBot</a> 用 ComfyUI 工作流、GPT-Image 或 Antigravity/Gemini 画画
</p>

<p align="center">
  <img alt="version" src="https://img.shields.io/badge/version-v1.15.1-d6303f?style=flat-square">
  <img alt="AstrBot" src="https://img.shields.io/badge/AstrBot-plugin-c8283a?style=flat-square">
  <img alt="ComfyUI" src="https://img.shields.io/badge/ComfyUI-workflow-b11f31?style=flat-square">
  <img alt="cloud" src="https://img.shields.io/badge/云绘图-GPT--Image%20%7C%20Gemini-e0707b?style=flat-square">
  <img alt="python" src="https://img.shields.io/badge/python-3.10%2B-f2c2c6?style=flat-square">
</p>

---

## ✨ 能做什么

| | |
| --- | --- |
| 🎨 **本地 ComfyUI 出图** | 把自己的工作流导出成 API 格式丢进文件夹，`/绘图 提示词` 就能用；支持多工作流切换、参数注入、LoRA 叠加、图生视频。 |
| ☁️ **云绘图** | `/云绘图` 接 GPT-Image 或 Sub2API Antigravity/Gemini；引用或附带原图时自动改成图片编辑。 |
| 🧸 **一键预设** | `--巫女`、`--符卡`、`--手办`、`--黏土`、`--像素`… 二十多种风格预设（含 4 个博丽神社限定），`/变手办` 直接把原图变成收藏级手办。 |
| 🎀 **博丽灵梦风卡片** | 帮助、工作流列表、ComfyUI 状态、云绘图方案，连报错和提示都用红白巫女风格的图片卡片回复，渲染失败自动退回文字。 |
| 🌸 **二次元的我** | 每人每天抽一张自己的二次元形象，附资料卡。 |

## 🖼️ 效果展示

下面的图全部由本插件的云绘图接口生成，主角是博丽灵梦；除第一张外都直接使用插件内置预设的提示词（`tools/art_prompts.json`）。

<table>
  <tr>
    <td align="center"><img src="assets/showcase/anime.jpg" width="240"><br><code>/云绘图 灵梦</code><br>默认日系画风</td>
    <td align="center"><img src="assets/showcase/figure.jpg" width="240"><br><code>--手办</code><br>收藏级 PVC 手办</td>
    <td align="center"><img src="assets/showcase/clay.jpg" width="240"><br><code>--黏土</code><br>Q 版黏土人</td>
  </tr>
  <tr>
    <td align="center"><img src="assets/showcase/pixel.jpg" width="240"><br><code>--像素</code><br>复古像素画</td>
    <td align="center"><img src="assets/showcase/sticker.png" width="240"><br><code>--贴纸</code><br>模切贴纸</td>
    <td align="center"><img src="assets/showcase/watercolor.jpg" width="240"><br><code>--水彩</code><br>水彩插画</td>
  </tr>
  <tr>
    <td align="center"><img src="assets/showcase/miko.jpg" width="240"><br><code>--巫女</code><br>红白巫女装束</td>
    <td align="center"><img src="assets/showcase/shrine.jpg" width="240"><br><code>--参拜</code><br>博丽神社参拜</td>
    <td align="center"><img src="assets/showcase/spellcard.jpg" width="240"><br><code>--符卡</code><br>弹幕符卡宣言</td>
  </tr>
</table>

---

## 这是什么

你只需要把自己在 ComfyUI 里搭好的工作流导出成 **API 格式**，在要动态替换的地方留几个占位符，剩下的交给插件：用户发 `/绘图 ...`，插件把参数填进工作流、提交给 ComfyUI、等待出图、再把图片发回聊天里。

> 协议端用 [LLOneBot / LuckyLilliaBot](https://github.com/LLOneBot/LuckyLilliaBot)（OneBot v11）完全没问题。插件是「协议无关」的——发图走 AstrBot 的统一消息层，你只要在 AstrBot 里把 **OneBot v11（aiocqhttp）** 平台连上 LuckyLilliaBot 即可，插件本身不用关心是哪个协议端。

---

## 安装

把整个 `astrbot_plugin_comfyui_draw` 文件夹放到 AstrBot 的 `data/plugins/` 目录下：

```
AstrBot/
└── data/
    └── plugins/
        └── astrbot_plugin_comfyui_draw/
            ├── main.py            # 指令入口
            ├── cloud_backend.py   # 云端绘图接口
            ├── comfy_backend.py   # 本地 ComfyUI 与工作流注入
            ├── usage.py           # 排队、限流、每日次数与出图记录
            ├── draw_queue.py
            ├── errors.py
            ├── presets.py
            ├── templates.py
            ├── metadata.yaml
            ├── _conf_schema.json
            ├── requirements.txt
            ├── logo.png
            ├── assets/          # 横幅、卡片插画、效果示例图
            ├── tools/           # 美术图生成脚本（可选，运行插件不需要）
            └── README.md
```

然后在 AstrBot WebUI 的插件页面重载插件（或重启 AstrBot）。

> 从 v1.11.2 起插件由多个 `.py` 文件组成，手动升级时请替换整个文件夹，不要只覆盖 `main.py`。

---

## 配置（WebUI → 插件 → 本插件 → 配置）

| 配置项 | 说明 |
| --- | --- |
| `comfyui_base_url` | ComfyUI 地址，如 `127.0.0.1:8188` 或 `http://192.168.1.10:8188`。**是 AstrBot 所在机器去访问它**。 |
| `workflow_dir` | **工作流文件夹**（推荐）。指向一个存放 API 格式 `.json` 工作流的文件夹，里面每个 `.json` 自动成为一套工作流，文件名即工作流名。需与 AstrBot 在同一台机器；改文件即时生效。 |
| `default_workflow_name` | 不带 `-w` 时默认用哪套命名工作流（填文件名或 `extra_workflows` 里的名称）。 |
| `default_workflow` | 默认工作流（API 格式 JSON，见下）。留空则用内置的 SD1.5 文生图示例。 |
| `extra_workflows` | 额外的命名工作流（直接把 JSON 粘进配置），调用时用 `-w 名称` 选择。 |
| `default_negative_prompt` | 默认负向提示词。 |
| `default_width` / `default_height` | 默认尺寸（会自动取 8 的倍数，范围 64–2048）。 |
| `default_steps` / `default_cfg` / `default_batch_size` | 默认步数 / CFG / 张数。 |
| `max_batch_size` | 单次允许的最大张数。 |
| `max_steps` / `max_cfg` | 最终工作流允许的最大步数 / CFG，防止异常任务长时间占用显卡。 |
| `max_total_pixels` | 单任务最大总像素量，按 宽×高×张数 计算。 |
| `max_prompt_length` / `max_loras` | 提示词最大字符数 / 单任务最多叠加 LoRA 数。 |
| `max_input_size_mb` / `max_output_size_mb` | 单张输入图 / 单个输出文件的体积上限。 |
| `auto_randomize_seed` | 每次自动随机种子（默认开）。 |
| `max_concurrent_tasks` / `max_concurrent_cloud_tasks` | 本地 ComfyUI / 云端各自同时进行的任务数，默认都是 2；两边分开排队，云端慢不会堵住本地。超出的任务会提示排队位置。 |
| `max_tasks_per_user` | 每人同时在生成和排队的任务数上限（本地与云端合计），默认 1；0 不限。管理员不受限。 |
| `user_cooldown_seconds` | 每人两次出图请求的最短间隔（秒），默认 0（不限）。管理员不受限。 |
| `max_queue_size` | 本地、云端各自最多排队任务数，默认 20；满了提示稍后再试。0 不限。 |
| `daily_limit_local` / `daily_limit_cloud` | 每人每天本地 / 云端最多出图张数，按成功张数计、0 点清零，默认 0（不限）。管理员和「二次元的我」不计入。 |
| `history_size` | 每人保留几条出图记录供 `/重画`、`/我的绘图` 使用，默认 10；只存描述和参数，不存图片。0 关闭。 |
| `timeout` | 单次生成超时（秒）。 |
| `text_as_card` | 文字回复（报错、权限、切换结果、用法等）改用博丽灵梦图片卡片，默认开；渲染失败自动退回文字。「正在生成」进度提示和出图结果下的参数说明始终是文字。 |
| `help_card_theme` | `/绘图帮助` 卡片主题：`默认`（淡紫蓝画室）、`神社`（朱红和纸、鸟居与注连绳）或 `博丽灵梦`（红白巫女、蝴蝶结、阴阳玉与赛钱箱，新安装的默认值）。可用 `/绘图主题` 在线切换。 |
| `active_cloud_profile` | 当前使用的云绘图方案名；留空使用下面的默认云绘图配置。可用 `/云绘图切换` 在线修改。 |
| `cloud_profiles` | 云绘图方案列表，每套可单独设置接口类型、地址、Key 和模型；留空项沿用默认配置。方案填了自己的地址时必须同时填 Key，不会借用顶层 Key。 |
| `openai_image_provider` | 云端绘图接口类型：`auto`、`openai-compatible` 或 `sub2api-antigravity`。 |
| `openai_image_base_url` | 云端绘图接口基址。`auto` 模式下根地址返回 404/405 时会自动改试 `/v1` 路径。默认留空。 |
| `openai_image_api_key` | 云端绘图通用 API Key（Bearer Token）。`auto` 模式始终使用它；其他接口类型的专属 Key 留空时也使用它。**按量付费，调用会消耗额度。** |
| `openai_compatible_api_key` / `sub2api_antigravity_api_key` | OpenAI 兼容和 Sub2API Antigravity 的专属 API Key，按 `openai_image_provider`（或方案的接口类型）自动选用；留空沿用通用 Key。 |
| `openai_image_model` | 云端绘图模型名，如 `gpt-image-2`。 |
| `cloud_default_art_style` | 云绘图默认美术风格，默认日系二次元插画。普通 `/云绘图` 未使用预设或 `--style` 时追加到提示词；描述中写明其他画风时以描述为准，清空则不追加。 |
| `openai_image_size` | 云端文生图默认尺寸；GPT-Image 2 还支持符合限制的自定义宽高。 |
| `openai_image_edit_max_inputs` | 云端图片编辑最多读取几张原图，默认 4；支持当前消息和引用消息。 |
| `openai_image_edit_use_source_size` | 图生图未写 `--size` 时沿用第一张原图分辨率，默认开启。 |
| `openai_image_timeout` | 云端绘图超时（秒），默认 360；从轮到该任务开始计时，排队时间不算。 |
| `enable_local_draw` / `enable_cloud_draw` | 本地绘图（ComfyUI）/ 云绘图的总开关，默认都开。关闭后对应的指令、AI 绘图工具、`/重画` 和「二次元的我」都会提示已关闭，对管理员同样生效。可用 `/绘图开关` 在线切换。 |
| `enable_access_control` | 启用白名单访问控制（默认关，关时所有人可用）。 |
| `user_whitelist` | 个人白名单（用户 ID 列表），这些用户私聊 / 群聊都能用。 |
| `group_whitelist` | 群白名单（群 ID 列表），这些群里所有人都能用。 |
| `access_deny_notice` | 无权限时是否回复提示（默认开；关则静默忽略）。 |
| `show_progress` / `auto_recall_progress` | 是否发送「正在生成」提示 / 生成结束后自动撤回该提示。 |
| `progress_recall_delay_ms` | 生成结束后撤回进度消息的延迟，默认 200 毫秒。 |
| `daily_me_backend` | 「二次元的我」生成来源：`comfyui`（本地工作流）或 `cloud`（云绘图）。 |
| `daily_me_cloud_size` | 「二次元的我」走云绘图时的尺寸，默认 `1024x1024`。 |
| `daily_me_result_card` / `daily_me_reply_source` | 把每日角色资料渲染成图片卡片，并引用用户的原消息回复；卡片后仍附带完整分辨率原图。 |
| `send_seed_info` | 出图后是否附带参数信息。 |

### 两种提供工作流的方式

无论哪种，工作流都必须是 ComfyUI 的 **API 格式**：在 ComfyUI 设置里勾选 **Enable Dev mode Options**，再点 **Save (API Format)** 导出。（普通的 “Save” 导出的是带 `nodes`/`links` 的网页格式，插件会识别并提示你重新导出。）

**方式一：从文件夹加载（推荐，免改 JSON）**

把导出的 `.json` 直接丢进一个文件夹，在配置 `workflow_dir` 里填这个文件夹路径，例如 `H:\AI\个人工作流`（也可写 `H:/AI/个人工作流`）。然后：

- 文件夹里每个 `.json` 自动成为一套工作流，**文件名（去掉 .json）就是工作流名**。比如 `小叶子.json` → 用 `-w 小叶子` 调用。
- 这种工作流**不需要手动加占位符**。插件会顺着采样器（KSampler 等）的 `positive` / `negative` 连线，自动把提示词填进对应的 CLIPTextEncode 节点；其余参数（尺寸、步数、CFG、采样器、LoRA 等）**沿用你在 ComfyUI 里调好的值**，只有当你在命令里显式写了 `--size` / `--steps` / `--cfg` / `--neg` / `--batch` 时才覆盖。
- 种子：默认每次随机（`auto_randomize_seed`），用 `--seed N` 可固定复现。
- 改动或新增文件**即时生效**，不用重载插件。把 `default_workflow_name` 设成某个文件名，不带 `-w` 的 `/绘图` 就默认用它。

> 前提：`workflow_dir` 是 **AstrBot 进程能直接读到的本地路径**，所以该文件夹要和 AstrBot 在同一台机器上。如果 AstrBot 和你存工作流的机器不是同一台，把文件复制到 AstrBot 那台机器再填路径，或改用方式二。
>
> 如果某个工作流结构特殊、自动定位不到正向提示词节点，插件会提示你——这时在该 `.json` 里把正向节点的 `text` 改成 `"%prompt%"` 即可（见方式二）。

**方式二：把 JSON 粘进配置 + 占位符**

适合不方便用文件夹、或想精确控制注入位置的场景。把 API 格式 JSON 粘到 `default_workflow`（或 `extra_workflows` 的某一项）里，再把要动态替换的地方改成占位符（**占位符要带引号**，保证 JSON 合法）。含占位符的工作流走占位符替换，缺省值由上面的 `default_*` 配置补全：

| 占位符 | 含义 | 类型 |
| --- | --- | --- |
| `"%prompt%"` | 正向提示词 | 文本 |
| `"%negative_prompt%"` | 负向提示词 | 文本 |
| `"%seed%"` | 随机种子 | 数字 |
| `"%width%"` / `"%height%"` | 宽 / 高 | 数字 |
| `"%steps%"` | 采样步数 | 数字 |
| `"%cfg%"` | CFG | 数字 |
| `"%batch_size%"` | 张数 | 数字 |

例如把 KSampler 节点里的 `"seed": 12345` 改成 `"seed": "%seed%"`，把正向 CLIPTextEncode 的 `"text": "..."` 改成 `"text": "%prompt%"`。文本占位符也支持嵌进一段话里，例如 `"text": "masterpiece, best quality, %prompt%"`。

> 不填 `default_workflow` 也能直接用——内置示例需要 `v1-5-pruned-emaonly.safetensors` 这个 checkpoint。换成你自己的工作流后就不受此限制。

---

## 使用

```
/绘图 a cute cat, masterpiece, best quality
/绘图 a girl in red dress --neg lowres, blurry --size 768x512 --steps 25 --cfg 7
/绘图 电影感山谷 --宽屏 -w 鬼针草-极速
/绘图 cyberpunk city --seed 12345        # 固定种子，便于复现
/绘图 anime girl -w anime                # 用名为 anime 的额外工作流
/绘图列表                                 # 查看可用工作流
/绘图状态                                 # 检查 ComfyUI 是否在线
/重画                                     # 用上一次的描述和参数再画一次
/重画 3 加上猫耳 --竖图                    # 重画第 3 条记录，补充描述并改成竖图
/我的绘图                                 # 查看最近出图记录和今日剩余次数
/绘图队列                                 # 查看谁在画、谁在排队
/绘图队列 取消 12                          # 取消编号 #12 的任务
/绘图帮助                                 # 查看完整使用帮助
```

行内参数：

| 参数 | 作用 |
| --- | --- |
| `--neg` / `--no` | 负向提示词（可多词，直到下一个参数为止） |
| `--size` | 尺寸，如 `--size 768x512` |
| `--横图` / `--landscape` | 横图快捷尺寸：本地 `1216x832`，云绘图 `1536x1024` |
| `--竖图` / `--portrait` | 竖图快捷尺寸：本地 `832x1216`，云绘图 `1024x1536` |
| `--方图` / `--square` | 方图快捷尺寸：`1024x1024` |
| `--宽图` / `--宽屏` / `--wide` | 宽屏快捷尺寸：本地 `1344x768`，云绘图 `1536x1024` |
| `--steps` | 采样步数 |
| `--cfg` | CFG 数值 |
| `--seed` | 固定种子 |
| `--batch` / `-b` | 生成张数（受 `max_batch_size` 限制） |
| `-w` / `--wf` | 选择工作流名 |
| `--lora` / `-l` | 临时加 LoRA，可重复，如 `--lora styleA:0.8` |
| `--preset` / `--预设` | 云绘图提示词预设，如 `--预设 手办`；也可直接写 `--手办`。 |

尺寸参数按从左到右处理，后写的覆盖前面的。例如 `--横图 --size 768x512`
最终使用 `768x512`；`--size 768x512 --竖图` 最终使用竖图预设。

指令一览（含别名）：

| 指令 | 作用 | 别名 |
| --- | --- | --- |
| `/绘图` | 出图（本地 ComfyUI） | `/draw`、`/comfyui`、`/comfy` |
| `/云绘图` | 用云端 GPT-Image 接口出图（按量付费） | `/gptdraw`、`/gptimage`、`/clouddraw` |
| `/变手办` | 引用或附带原图，一键用云端图片编辑转换成手办 | `/手办化`、`/figureme` |
| `/云绘图预设` | 用图片卡片查看云绘图预设、尺寸与使用示例 | `/云预设`、`/gpt预设` |
| `/云绘图切换` | 查看云绘图方案；管理员可切换方案（可同时指定模型），全局生效 | `/云切换`、`/cloudswitch` |
| `/云绘图模型` | 查看当前方案的模型；管理员可修改，全局生效 | `/云模型`、`/cloudmodel` |
| `/绘图列表` | 查看可用工作流 | `/drawlist`、`/comfyui_list` |
| `/绘图状态` | 检查 ComfyUI 是否在线 | `/drawstatus`、`/comfystatus` |
| `/重画` | 用上一次（或第 N 条记录）的描述和参数再画一次；可补充描述或改参数。本地重画默认换随机种子；原图编辑需重新引用原图 | `/再画一张`、`/redraw` |
| `/我的绘图` | 查看自己最近的出图记录和今日剩余次数；`/我的绘图 清空` 删除自己的记录 | `/绘图记录`、`/drawhistory` |
| `/绘图队列` | 查看本地与云端正在生成和排队的任务；`/绘图队列 取消 <编号>` 取消自己的任务，管理员可取消任何人的 | `/绘图排队`、`/drawqueue` |
| `/绘图开关` | 查看本地绘图和云绘图是否开启；管理员可单独开关，如 `/绘图开关 云端 关`，全局生效并写回配置 | `/drawswitch` |
| `/绘图主题` | 查看帮助卡片主题；仅管理员可切换（默认 / 神社 / 博丽灵梦），全局生效 | `/帮助主题`、`/drawtheme` |
| `/绘图默认` | 所有人可查看；仅管理员可切换默认工作流并持久保存 | `/drawdefault`、`/setdefault` |
| `/绘图帮助` | 查看完整使用帮助（含当前可用工作流） | `/drawhelp`、`/comfyhelp` |

切换默认工作流（不带 `-w` 时 `/绘图` 用哪一套），两种方式：

```
/绘图默认            # 查看当前默认 + 可选项
/绘图默认 鬼针草      # 管理员：切到鬼针草并写回配置（持久保存）
/绘图默认 默认        # 管理员：恢复为内置 / 配置的 default_workflow
```

也可以直接在插件配置面板里改 `default_workflow_name`（效果相同）。临时换一次则用 `/绘图 提示词 -w 名称`，不影响默认。

## 二次元的我

发送 `/二次元的我`，会按“用户 ID + 当天日期”生成当天固定的角色设定，每人每天一次。
角色从发色、发型、瞳色和表情中随机抽取，同时使用协调好的主题套装组合服装、配饰、动作、场景和光线，避免出现冬装配海边、魔女帽重复、赛车服进图书馆等割裂画面。
抽取结果会引用用户的触发消息回复：先发送包含主题、形象、造型、场景、参数和图片预览的资料卡，再附带完整分辨率原图。
插件会为该指令自动加入去文字、去水印、去 Logo 和去签名的专用负面词。可在配置 `daily_me_negative_prompt` 中修改；显式留空则沿用工作流原本的负面词。

生成来源可在 `daily_me_backend` 中切换：

- `comfyui`：使用 `daily_me_workflow` 指定的本地工作流。
- `cloud`：使用已配置的云绘图接口，包括 OpenAI 兼容接口或 Sub2API Antigravity；尺寸由 `daily_me_cloud_size` 控制。标签式角色设定会自动包装为自然语言提示词，负面词会转换为“不要出现”的要求。

两种来源都会保留每日一次限制、资料卡、引用原消息和完整分辨率原图。云绘图会消耗对应接口额度。

内置主题包括校园晨光、午后咖啡、神社初愿、夏夜祭典、霓虹夜行、海风黄昏、静谧书页、星空天台、冬日暖意、玻璃花房、深海蓝境、月夜魔法、闪耀舞台、灯火长街、枫色物语、雨声漫步、深夜便利店和蔷薇庭院。

## 临时加 LoRA

不用回 ComfyUI 改工作流，画图时用 `--lora` 直接加：

```
/绘图 1girl --lora myStyle           # 用默认权重（default_lora_strength，默认 0.8）
/绘图 1girl --lora myStyle:0.6       # 指定权重
/绘图 1girl --lora a:0.8 --lora b:0.5  # 叠加多个
```

- LoRA 名称要与 ComfyUI `models/loras` 目录里的文件一致；不带扩展名时自动补 `.safetensors`（如 `myStyle` → `myStyle.safetensors`）。
- 插件会以「仅模型」方式（`LoraLoaderModelOnly`）把 LoRA 插到工作流**模型链最前端**，原本用模型的节点（含已有 LoRA、各采样器）都会自动改接到新 LoRA 之后——所以对你那种带高清放大的多采样器工作流也整条生效。
- 想每次都加某个 LoRA：在配置 `default_loras` 里填（每行一个 `名称` 或 `名称:权重`）。
- 注意：插入的是「仅模型」LoRA（影响 UNet），不改 CLIP/文本编码；绝大多数画风 LoRA 这样就够。LoRA 的触发词仍要自己写进提示词。

## 云端绘图（GPT-Image / Antigravity，可选）

除了本地 ComfyUI，插件还支持调用 OpenAI 兼容的云端图片接口（如 `gpt-image-2`）和 Sub2API 的 Antigravity/Gemini 原生图片接口。

启用方法：在配置里填你所用服务的 `openai_image_base_url`、`openai_image_api_key`、`openai_image_model`（如 `gpt-image-2`），保存即可。然后：

```
/云绘图 一只戴贝雷帽的柴犬坐在咖啡馆窗边，水彩插画风
/云绘图 a poster that says "OPEN", flat design --size 1536x1024
/云绘图 银发少女，蓝色连衣裙 --手办
# 引用或附带一张原图后发送：
/变手办
/云绘图 --毛绒
```

- 常用尺寸档位为 `1024x1024`（方）、`1024x1536`（竖）、`1536x1024`（横）；GPT-Image 2 还支持符合限制的自定义宽高。用 `--size` 临时指定，`--batch N` 出多张。
- **这是按量付费接口，每次出图都会消耗你的 API 额度**，和免费的本地 ComfyUI 不同。
- AI 工具：同时提供了 `draw_image_gpt` 函数工具，可在人格里勾选，让 AI 在需要写实 / 带文字的图时自动用它（动漫画风仍走 `draw_image`）。

### 云绘图快捷预设

发送 `/云绘图预设` 可用 2 倍高清图片卡片查看完整列表、推荐尺寸及图生图示例；卡片使用 JPEG 95 高质量渲染，渲染失败时会自动退回文字。预设会自动扩写提示词，并在没有显式填写 `--size` 时选择推荐尺寸：

| 快捷参数 | 效果 | 推荐尺寸 |
| --- | --- | --- |
| `--巫女` / `--灵梦` | ⛩️ 博丽神社限定：红白巫女装束，博丽神社风 | 1024x1536 |
| `--参拜` / `--神社` | ⛩️ 博丽神社限定：博丽神社参拜的横版风景 | 1536x1024 |
| `--御守` / `--绘马` | ⛩️ 博丽神社限定：神社御守与绘马周边 | 1024x1024 |
| `--符卡` / `--弹幕` | ⛩️ 博丽神社限定：弹幕符卡宣言的华丽战斗场面 | 1536x1024 |
| `--手办` / `--变手办` | 收藏级 PVC 手办产品照 | 1024x1024 |
| `--黏土` | Q 版手工黏土人 | 1024x1024 |
| `--毛绒` | 柔软毛绒玩偶 | 1024x1024 |
| `--头像` | 精致社交头像 | 1024x1024 |
| `--海报` | 竖版电影宣传海报 | 1024x1536 |
| `--壁纸` | 横版桌面壁纸 | 1536x1024 |
| `--贴纸` | 粗描边模切贴纸 | 1024x1024 |
| `--像素` | 精细复古像素画 | 1024x1024 |
| `--盲盒` / `--潮玩` | 高级设计师盲盒玩具 | 1024x1024 |
| `--水彩` | 通透柔和水彩绘本 | 1024x1536 |
| `--赛博` / `--霓虹` | 电影级赛博霓虹夜景 | 1024x1536 |
| `--国风` / `--水墨` | 雅致新中式工笔水墨 | 1024x1536 |
| `--漫画` / `--复古漫画` | 高对比复古漫画封面 | 1024x1536 |
| `--油画` | 博物馆质感古典油画 | 1024x1536 |
| `--手机UI` / `--appui` | 高保真手机 App 界面 | 1024x1536 |
| `--网页UI` / `--webui` | 现代响应式网页界面 | 1536x1024 |
| `--后台UI` / `--dashboard` | 专业 SaaS 后台仪表盘 | 1536x1024 |
| `--数据大屏` / `--dataviz` | 科技感数据可视化大屏 | 1536x1024 |
| `--电商UI` / `--shopui` | 精致移动电商购物界面 | 1024x1536 |
| `--游戏UI` / `--gameui` | 沉浸式游戏菜单与 HUD | 1536x1024 |
| `--周边目录` / `--谷子海报` | 二次元官方周边贩售图鉴 | 1536x1536 |
| `--联动菜单` / `--咖啡菜单` | 二次元主题咖啡联动菜单 | 1536x1536 |

也可以使用通用写法：`/云绘图 <主体描述> --预设 手办`。

当命令消息里附带图片，或命令引用了一条带图片的消息时，插件会自动从文生图切换到云端图片编辑接口：

```text
引用原图 → /变手办
引用原图 → /云绘图 --手办
引用原图 → /云绘图 改成冬日服装，保持人物和姿势不变
```

`/变手办` 会自动加入“尽量保留人物身份、脸部特征、发型、服装配色、姿势、机位和构图”的要求。图生图默认沿用第一张原图的宽高，手办等预设不会再强制改成方图；如果显式使用 `--size`、`--横图`、`--竖图` 等参数，则以手动尺寸为准。GPT-Image 2 的自定义尺寸需要符合接口限制，因此不是 16 像素倍数或超出上限的原图会进行最小幅度调整。多图编辑最多读取 `openai_image_edit_max_inputs` 张，默认 4 张；重复图片自动忽略。是否能完全保持原脸仍取决于云端模型本身。

### 接入 Sub2API Antigravity

适用于 [Wei-Shaw/sub2api](https://github.com/Wei-Shaw/sub2api) 的 Antigravity 分组。`Antigravity-Pro` 是站点分组名称，不是请求使用的模型名。

在插件配置里填写：

| 配置项 | 填写内容 |
| --- | --- |
| `openai_image_provider` | `sub2api-antigravity` |
| `openai_image_base_url` | 你的 Sub2API 站点根地址，例如 `https://api.example.com` |
| `sub2api_antigravity_api_key` | 绑定到可用 Antigravity 分组的 Sub2API API Key（留空则使用 `openai_image_api_key`） |
| `gemini_image_model` | 默认 `gemini-3.1-flash-image`，按站点模型列表调整，也可使用站点支持的 `gemini-3-pro-image` 等图片模型 |
| `gemini_image_resolution` | `1K`、`2K` 或 `4K`，默认 `1K`；以模型和站点支持情况为准 |
| `gemini_image_aspect_mode` | 默认 `auto`；不支持比例参数的模型可选 `prompt`；`strict` 不做兼容回退 |
| `openai_image_timeout` | 默认 360 秒；上游较慢时可适当提高 |

接口地址可带 `/v1`、`/antigravity`、`/antigravity/v1beta`，插件会统一构造：

```text
POST /antigravity/v1beta/models/{模型名}:generateContent
Authorization: Bearer <Sub2API API Key>
```

文生图与原图编辑都走 Gemini 原生格式；引用/附带图片会通过 `contents.parts.inlineData` 上传，输出读取 `candidates[].content.parts[].inlineData`，思考阶段预览图不作为最终结果发送。不会把 Antigravity 请求发往 `/v1/images/generations` 或 `/v1/images/edits`。

```text
/云绘图 粉发少女站在盛开的樱花树下，远景全身，树冠和树干清晰可见 --横图
/云绘图 二次元咖啡店联动菜单 --联动菜单 --quality 2K
/云绘图 蓝色星空壁纸 --size 16:9 --quality 2K
# 引用/附带 PNG、JPEG 或 WebP 原图后发送：
/变手办
/云绘图 保留人物脸部，换成冬日服装 --quality 2K
```

- `--size` 的宽高及原图宽高会转换到最接近的模型支持比例；清晰度由 `gemini_image_resolution` 或命令 `--quality 1K/2K/4K` 控制。**不是按任意指定像素输出，也不能保证与原图分辨率完全相同**。资料卡显示实际返回的图片宽高。
- 本模式使用独立的 `gemini_image_model`，保留原来的 `openai_image_model` 供切回 GPT-Image 时使用；OpenAI 默认 `quality` 配置不参与 Gemini 请求，`response_format` 也不参与。
- `--batch N` 会逐张调用，全部张数共享云绘图超时预算；后续失败会提示并发送已完成图片，不自动重试。生成多张或选择高分辨率可能增加费用与耗时。
- 若接口明确返回 HTTP 400 `Aspect ratio is not enabled for this model`，`auto` 模式会只去掉被拒绝的 `aspectRatio`，将比例改为提示词描述后再尝试一次；本次加载期间记住此接口/模型的限制。`prompt` 模式从首次请求就省略比例字段，适合已知不支持该参数的渠道。这两种兼容行为无法保证精确输出比例；超时、限流、其他 400 或 5xx 不会触发自动重试。
- 提示词很短（例如只写一个角色名）时，Gemini 偶尔会把请求当成聊天、只回复文字不出图。插件会在请求里明确要求输出图片；若仍只收到文字，默认自动再要求出图一次（`gemini_text_only_retry`，可关闭）。安全拦截、超时和限流不会触发这次重试。把画面描述写具体（外貌、动作、场景、画风）最稳妥。
- 模型名以站点实际提供为准，名字中带 `image` 不代表上游一定支持生图；若兼容后仍没有最终图片，需检查站点模型映射。插件不会自动切换到其他模型。
- 手办、毛绒、海报、UI 等预设继续可用；`daily_me_backend=cloud` 时，「二次元的我」也使用此渠道，保留每日一次、引用回复、资料卡与原图。
- Sub2API 管理员需要允许对应分组绘图、放行模型，并保证上游账号有对应模型权限和额度。404 请检查站点地址和版本；403 请检查 Key、分组权限及模型白名单。
- 余额与额度请在 Sub2API 控制台查看。此次适配使用离线响应模拟验证，未调用用户的付费接口；实际可用模型以你的站点为准。

### 在线切换云绘图方案

可以在插件配置的 `cloud_profiles` 中保存多套云绘图接口，例如：

| 方案名 | 接口类型 | 地址 / Key | 模型 |
| --- | --- | --- | --- |
| GPT | `openai-compatible` | OpenAI 兼容接口的地址和 Key | 留空（沿用 `openai_image_model`） |
| Gemini | `sub2api-antigravity` | Sub2API 站点地址和 Key | `gemini-3-pro-image` |

方案里留空的地址、Key、模型会沿用上面的默认云绘图配置；顶层配置本身就是名为「默认」的方案。

```text
/云绘图切换                       # 所有可用绘图的人都能查看方案列表和当前方案
/云绘图切换 Gemini                # 管理员：切换到 Gemini 方案
/云绘图切换 GPT gpt-image-2       # 管理员：切换方案并同时指定模型
/云绘图切换 默认                  # 管理员：回到默认配置
/云绘图模型 gemini-3.1-flash-image  # 管理员：只修改当前方案的模型
```

- 切换和改模型对所有群聊、私聊立即生效，并写回插件配置，重启后保留。
- 聊天里只显示方案名、接口类型和模型，不会显示地址或 Key。
- `/云绘图`、`/变手办`、云端「二次元的我」都使用当前方案。
- 不同站点请分别填写 Key，避免把一个站点的 Key 发给另一个站点。

## 访问控制（白名单）

默认所有人都能用绘图。如果想限制，打开 `enable_access_control`，然后：

- `user_whitelist`：填用户 ID（每行一个）。名单里的用户在私聊和群聊都能用。用 `/sid` 指令可查到自己的 ID。
- `group_whitelist`：填群 ID（每行一个）。名单里的群，群内所有人都能用。

放行规则：**AstrBot 管理员（超级用户）始终不受限**；其次是个人白名单用户；再次是群白名单所在的群；其余一律拦截。被拦截时默认回复一句『无权限』，可用 `access_deny_notice` 关掉改成静默忽略。

> 说明：白名单控制 `/绘图`、`/云绘图`、`/二次元的我` 和两个 AI 绘图工具；`/绘图默认` 可公开查看，但修改全局默认值始终只允许管理员。只读的 `/绘图列表`、`/绘图状态`、`/绘图帮助` 不受限。管理员名单在 AstrBot「配置 → 其他配置 → 管理员 ID 列表」里设置（用 `/op` 或填 ID）。

## 排队与限流

本地 ComfyUI 和云端各有一个队列，先到先得。轮不到时会先发一条「⏳ 排队中：第 N 位」，轮到后撤回并换成「🎨 正在生成」；超时从轮到时开始计时。每人同时只能有 `max_tasks_per_user` 个任务，还可以用 `user_cooldown_seconds` 设冷却、用 `daily_limit_cloud` 控制每人每天的云端张数。以上限制对 AstrBot 管理员不生效。

`/绘图队列 取消` 能取消排队中的任务；已经开始的任务也能取消，但请求已经发出，云端可能仍会计费，ComfyUI 可能仍会把图跑完。

出图记录（`draw_history.json`）和每日次数（`draw_usage.json`）同样保存在下面的 data 目录。

「二次元的我」使用记录保存在 `data/plugin_data/astrbot_plugin_comfyui_draw/`，采用并发预占和原子写入；插件更新或重装不会覆盖记录。

---

## 常见问题

- **连不上 ComfyUI**：先发 `/绘图状态`。确认 `comfyui_base_url` 正确、ComfyUI 已启动，且 **AstrBot 所在机器**能访问到它（Docker 部署时注意 `127.0.0.1` 指向的是容器内部，跨容器要用宿主机 IP 或服务名）。
- **文件夹里的工作流没出现在 `/绘图列表`**：确认 `workflow_dir` 路径正确、是 **AstrBot 那台机器**上的本地路径、文件是 `.json` 后缀；改完配置后保存即可（文件本身改动无需重载）。
- **提示「这看起来是普通工作流 / 不是 API 格式」**：你导出的是网页格式。回 ComfyUI 勾选 **Enable Dev mode Options**，用 **Save (API Format)** 重新导出覆盖原文件。
- **提示「没能自动定位正向提示词节点」**：该工作流结构较特殊。在它的 `.json` 里把正向提示词节点的 `"text": "..."` 改成 `"text": "%prompt%"`（负向用 `"%negative_prompt%"`），插件就会按占位符注入。
- **提示「没有取到图片」**：工作流里要有 `SaveImage`（或同类输出）节点。
- **每次出图都一样**：确认 `auto_randomize_seed` 开着，或（占位符工作流）用了 `"%seed%"`。
- **想让出图用工作流自己调好的尺寸/步数**：用文件夹方式加载即可，不写 `--size`/`--steps` 就会沿用原值。
- **节点报错 / 校验失败**：插件会把 ComfyUI 返回的 `node_errors` 透传出来，按提示检查模型名、节点连线等。
- **JSON 解析失败**：确认导出的是「API 格式」而不是普通工作流；若用了占位符，确保都带引号。

---

## 工作原理

提交 `POST /prompt` → 通过 `ws://.../ws` 监听执行完成 → `GET /history/{id}` 取输出 → `GET /view` 下载图片 → 用 AstrBot 消息链把图片发回会话。全程异步（aiohttp），不会阻塞机器人。

---

## 重新生成美术图

logo、横幅、帮助卡插画和效果示例图都是用插件自己的云绘图接口画的，提示词在 `tools/art_prompts.json`。想换主角或重画时，在插件根目录执行：

```bash
IMAGE_BASE_URL=http://你的接口/v1 IMAGE_API_KEY=你的Key python tools/gen_art.py           # 全部重画
IMAGE_BASE_URL=... IMAGE_API_KEY=... python tools/gen_art.py logo banner                  # 只画指定几张
```

脚本只用标准库，Key 只从环境变量读取，不会写进文件。画完 `help` 后，装了 Pillow 的话脚本会顺手把它缩成卡片用的小头像 `assets/reimu_avatar.jpg`；删掉这个文件，卡片就不显示插画。
