from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TMP_ROOT = PROJECT_ROOT / "tmp"


def _get_safe_tmp_root() -> Path:
    is_junction = getattr(TMP_ROOT, "is_junction", lambda: False)
    if TMP_ROOT.is_symlink() or is_junction():
        raise ValueError("临时目录不安全")
    return TMP_ROOT.resolve()


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
    resolved_root = _get_safe_tmp_root()
    if resolved_root not in resolved_path.parents:
        raise ValueError("路径不安全")
    return resolved_path


def resolve_tmp_path(relative_path: str) -> Path:
    resolved_root = _get_safe_tmp_root()
    candidate = (resolved_root / relative_path).resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise ValueError("路径不安全")
    return candidate
