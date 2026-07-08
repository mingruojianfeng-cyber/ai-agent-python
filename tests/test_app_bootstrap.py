from fastapi import FastAPI


def test_app_main_exposes_fastapi_application() -> None:
    from app.main import app

    assert isinstance(app, FastAPI)
    assert app.title == "Yu AI Agent Python"

