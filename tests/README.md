# 离线测试

在插件仓库根目录使用 Python 3.10 或更高版本运行：

```text
python tests/test_optimized_plugin.py
python tests/test_sub2api_antigravity.py
python tests/test_cloud_and_inputs.py
python tests/test_cloud_profiles.py
python tests/test_help_theme.py
```

测试使用 AstrBot/aiohttp 替身和虚构的 API Key，不连接真实出图服务，不消耗接口额度。

- `test_optimized_plugin.py`：原有尺寸、工作流参数、权限、每日限制、进度撤回和图片卡片回归检查。没有 `tests/actual_workflows/` 时自动跳过本地工作流样本检查。
- `test_sub2api_antigravity.py`：19 项配置与请求模拟检查，覆盖原生 Gemini 格式、参考图上传、比例映射、图片解析、批量失败、总超时，以及比例参数被拒绝时的有限回退。
- `test_cloud_and_inputs.py`：云端接口 `/v1` 回退（含 HTML 404）、非 JSON 错误、图片扩展名、`file:///` 本地原图、ComfyUI 非 JSON 响应及尺寸解析回归检查。
- `test_cloud_profiles.py`：云绘图方案继承与回退、按方案发送请求、`/云绘图切换` 与 `/云绘图模型` 的权限、写回和隐私检查。
- `test_help_theme.py`：帮助卡片主题选择与回退、神社模板完整渲染全部帮助内容、`/绘图主题` 的权限与写回。

测试会像 AstrBot 一样把插件目录作为包加载，因此 `main.py` 可以相对导入 `presets.py` 与 `templates.py`。
