from html import escape

from pydantic import BaseModel, Field
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate

from app.tools.common import resolve_tool_path


class GeneratePdfArgs(BaseModel):
    """生成 PDF 工具的入参。"""

    file_name: str = Field(min_length=1, description="要生成的 PDF 文件名")
    content: str = Field(description="要写入 PDF 的文本内容")


def _ensure_chinese_font() -> None:
    if "STSong-Light" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


def generate_pdf(args: GeneratePdfArgs) -> str:
    """在 tmp/pdf 中生成支持中文内容的 PDF。"""
    try:
        path = resolve_tool_path("pdf", args.file_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        _ensure_chinese_font()
        style = ParagraphStyle(
            "中文正文",
            parent=getSampleStyleSheet()["BodyText"],
            fontName="STSong-Light",
            leading=18,
        )
        document = SimpleDocTemplate(str(path))
        content = escape(args.content).replace("\n", "<br/>")
        document.build([Paragraph(content, style)])
        return f"PDF 生成成功：{path}"
    except (OSError, ValueError) as exc:
        return f"生成 PDF 失败：{exc}"
