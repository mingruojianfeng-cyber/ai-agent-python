# Path 是跨平台路径对象，避免手工拼接 Windows/Unix 分隔符。
from pathlib import Path


# __file__ 是当前模块路径；resolve 消除相对路径和链接，parents[2] 回到项目根目录。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# / 被 Path 重载为路径拼接运算符，不是字符串除法。
TMP_ROOT = PROJECT_ROOT / "tmp"


def _get_safe_tmp_root() -> Path:
    # is_junction 并非所有 Python/平台都有，getattr 提供兼容的默认检测函数。
    is_junction = getattr(TMP_ROOT, "is_junction", lambda: False)
    # 拒绝符号链接和 Windows junction，防止工具目录被重定向到敏感位置。
    if TMP_ROOT.is_symlink() or is_junction():
        raise ValueError("临时目录不安全")
    # 返回规范化绝对路径，为后续“是否仍位于根目录下”的安全比较提供基准。
    return TMP_ROOT.resolve()


def get_tool_tmp_dir(category: str) -> Path:
    # 按工具类别隔离临时文件，如 tmp/file、tmp/pdf、tmp/download。
    return TMP_ROOT / category


def resolve_tool_path(category: str, file_name: str) -> Path:
    # 先解析用户文件名，再用多项规则拒绝路径穿越和绝对路径。
    candidate = Path(file_name)
    if (
        # 空文件名、任一目录分隔符、带目录的路径和绝对路径都不允许。
        not file_name
        or "/" in file_name
        or "\\" in file_name
        or candidate.name != file_name
        or candidate.is_absolute()
    ):
        raise ValueError("文件名不安全")
    # 只使用 candidate.name，确保攻击者不能借输入携带父目录。
    path = get_tool_tmp_dir(category) / candidate.name
    if path.is_symlink():
        raise ValueError("路径不安全")
    # strict=False 允许目标文件尚未创建，这对写文件工具是必要的。
    resolved_path = path.resolve(strict=False)
    resolved_root = _get_safe_tmp_root()
    # 规范化后仍必须是 tmp 根目录的后代，形成最后一道路径边界校验。
    if resolved_root not in resolved_path.parents:
        raise ValueError("路径不安全")
    return resolved_path


def resolve_tmp_path(relative_path: str) -> Path:
    # 先验证根目录本身没有被链接劫持。
    resolved_root = _get_safe_tmp_root()
    # 此接口允许子路径，所以先拼接再 resolve，以便识别 ../ 等逃逸行为。
    candidate = (resolved_root / relative_path).resolve()
    # 根目录自身合法；其他路径必须仍然位于根目录之下。
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise ValueError("路径不安全")
    return candidate
