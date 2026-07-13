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
    path = get_tool_tmp_dir(category) / candidate.name
    if path.is_symlink():
        raise ValueError("路径不安全")
    resolved_path = path.resolve(strict=False)
    resolved_root = TMP_ROOT.resolve()
    if resolved_root not in resolved_path.parents:
        raise ValueError("路径不安全")
    return resolved_path


def resolve_tmp_path(relative_path: str) -> Path:
    resolved_root = TMP_ROOT.resolve()
    candidate = (resolved_root / relative_path).resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise ValueError("路径不安全")
    return candidate
