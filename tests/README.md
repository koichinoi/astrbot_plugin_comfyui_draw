# 离线测试

在插件仓库根目录使用 Python 3.10 或更高版本运行（也可以一次跑完：`python -m unittest discover -s tests`）：

```text
python tests/test_optimized_plugin.py
python tests/test_sub2api_antigravity.py
python tests/test_cloud_and_inputs.py
python tests/test_gemini_text_only.py
python tests/test_cloud_profiles.py
python tests/test_help_theme.py
python tests/test_cloud_default_style.py
python tests/test_info_cards.py
python tests/test_queue_and_history.py
python tests/test_draw_switches.py
python tests/test_reimu_presets.py
python tests/test_preset_market.py
python tests/test_novelai.py
```

测试使用 AstrBot/aiohttp 替身和虚构的 API Key，不连接真实出图服务，不消耗接口额度。

- `test_optimized_plugin.py`：原有尺寸、工作流参数、权限、每日限制、进度撤回和图片卡片回归检查。没有 `tests/actual_workflows/` 时自动跳过本地工作流样本检查。
- `test_sub2api_antigravity.py`：19 项配置与请求模拟检查，覆盖原生 Gemini 格式、参考图上传、比例映射、图片解析、批量失败、总超时，以及比例参数被拒绝时的有限回退。
- `test_cloud_and_inputs.py`：云端接口 `/v1` 回退（含 HTML 404）、非 JSON 错误、图片扩展名、`file:///` 本地原图、ComfyUI 非 JSON 响应及尺寸解析回归检查。
- `test_gemini_text_only.py`：Gemini 只回文字时的出图要求、单次重试、拦截不重试、批量与部分结果。
- `test_cloud_profiles.py`：云绘图方案继承与回退、按接口类型选用专属 Key、按方案发送请求、`/云绘图切换` 与 `/云绘图模型` 的权限、写回和隐私检查。
- `test_help_theme.py`：帮助卡片主题选择与回退、神社模板完整渲染全部帮助内容、`/绘图主题` 的权限与写回。
- `test_info_cards.py`：`/绘图列表`、`/绘图主题`、`/云绘图切换` 的博丽灵梦信息卡片完整渲染、不泄露地址和 Key、渲染失败退回文字；普通文字回复的提示卡类型判断、转义与 `text_as_card` 开关。
- `test_queue_and_history.py`：排队顺序与位置提示、本地/云端分开排队、每人同时任务数、冷却、每日次数、`/绘图队列` 查看与取消、出图途中切换方案、`/重画` 与 `/我的绘图`。
- `test_draw_switches.py`：本地 / 云端开关分别拦截对应指令、AI 工具、`/重画` 与「二次元的我」，`/绘图开关` 的查看、权限与写回。
- `test_cloud_default_style.py`：默认画风只追加到普通文生图，预设、`--style`、原图编辑与「二次元的我」不受影响，可改可关。

测试会像 AstrBot 一样把插件目录作为包加载，因此 `main.py` 可以相对导入 `presets.py` 与 `templates.py`。
- `test_reimu_presets.py`：博丽神社限定预设（巫女、参拜、御守、符卡）的参数与别名、`/云绘图预设` 灵梦风卡片分组与缺图兜底、文字兜底分组。
- `test_preset_market.py`：预设市场索引校验（自带的 market/presets.json 不和内置预设重名）、`/预设搜索` 缓存、翻页与连不上时的提示、按编号或名字导入、导入后可用 `--名字`、重名拒绝、删除，以及 `/云绘图预设` 卡片和文字兜底的「已导入」分组。
- `test_novelai.py`：NAI 模型与提示词结构、种子 0、图生图参数、像素与步数限制、独立 Token、ZIP/JSON 解析、错误脱敏、串行调用、批量部分结果、总超时及二次元的我集成（19 项）。
