from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TMP_ROOT = PROJECT_ROOT / "tmp"


def get_tool_tmp_dir(category: str) -> Path:
    return TMP_ROOT / category


def resolve_tool_path(category: str, file_name: str) -> Path:
    candidate = Path(file_name)
    if (
        not file_name
        or "/" in file_name
        or "\\" in file_name
        or candidate.name != file_name
        or candidate.is_absolute()
    ):
        raise ValueError("文件名不安全")
    return get_tool_tmp_dir(category) / candidate.name


def resolve_tmp_path(relative_path: str) -> Path:
    candidate = (TMP_ROOT / relative_path).resolve()
    if candidate != TMP_ROOT and TMP_ROOT not in candidate.parents:
        raise ValueError("路径不安全")
    return candidate
