"""插件内部使用的可读错误类型。"""


class ComfyUIError(Exception):
    """ComfyUI 交互过程中的可读错误。"""
    pass


class DrawRejected(ComfyUIError):
    """限流、排队已满或每日次数用完；提示原样发给用户，不加「生成失败」前缀。"""
    pass


class GeminiTextOnlyError(ComfyUIError):
    """Gemini 正常结束但只回复了文字、没有图片（常见于提示词过短被当成聊天）。"""
    pass
