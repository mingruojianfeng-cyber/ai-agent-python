from app.tools.pdf_generation import GeneratePdfArgs, generate_pdf


def test_generate_pdf_writes_pdf_to_tmp(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.tools.common.TMP_ROOT", tmp_path)

    result = generate_pdf(GeneratePdfArgs(file_name="report.pdf", content="中文内容"))
    created = tmp_path / "pdf" / "report.pdf"

    assert "生成成功" in result
    assert created.read_bytes().startswith(b"%PDF")
