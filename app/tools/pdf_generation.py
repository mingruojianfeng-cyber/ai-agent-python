# escape 把用户文本中的 <、& 等转义，避免被 ReportLab Paragraph 当作 XML/HTML 标记解释。
from html import escape

from pydantic import BaseModel, Field
# ReportLab 样式 API 用于定义段落字体、行距等 PDF 排版参数。
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
# pdfmetrics 管理 ReportLab 已注册字体。
from reportlab.pdfbase import pdfmetrics
# UnicodeCIDFont 提供内置 CJK 字体支持，避免中文显示为方块。
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate

from app.tools.common import resolve_tool_path


class GeneratePdfArgs(BaseModel):
    """生成 PDF 工具的入参。"""

    file_name: str = Field(min_length=1, description="要生成的 PDF 文件名")
    content: str = Field(description="要写入 PDF 的文本内容")


def _ensure_chinese_font() -> None:
    # 先查询避免每次生成 PDF 重复注册同名字体。
    if "STSong-Light" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


def generate_pdf(args: GeneratePdfArgs) -> str:
    """在 tmp/pdf 中生成支持中文内容的 PDF。"""
    try:
        # 复用安全路径策略，将输出限制在 tmp/pdf。
        path = resolve_tool_path("pdf", args.file_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        # 先注册字体，后续 ParagraphStyle 才能按名称引用它。
        _ensure_chinese_font()
        # 基于 ReportLab 默认 BodyText 派生样式，只覆盖中文字体和行距。
        style = ParagraphStyle(
            "中文正文",
            parent=getSampleStyleSheet()["BodyText"],
            fontName="STSong-Light",
            leading=18,
        )
        # ReportLab 接受字符串路径，Path 需显式转换为 str。
        document = SimpleDocTemplate(str(path))
        # 转义后再把换行替换为 Paragraph 能识别的换行标签。
        content = escape(args.content).replace("\n", "<br/>")
        # build 接受 Flowable 列表；这里仅生成一个带样式的段落。
        document.build([Paragraph(content, style)])
        return f"PDF 生成成功：{path}"
    except (OSError, ValueError) as exc:
        return f"生成 PDF 失败：{exc}"
