# 使用 Python 标准库日志模块，不额外引入日志框架。
import logging


# %()s 占位符会在日志记录真正输出时由 LogRecord 的字段替换。
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(logger_name: str = "yu_ai_agent", level: str = "INFO") -> logging.Logger:
    # 参数默认值让调用方可直接获得项目默认日志器，也允许按模块覆盖名称与级别。
    # logging.getLogger 会按名称复用 Logger；同名调用不会重复创建实例。
    logger = logging.getLogger(logger_name)
    # 统一转大写，兼容调用方传入 info、Info 等写法。
    logger.setLevel(level.upper())
    logger.propagate = False

    # 防止应用重复初始化时不断追加 Handler，造成同一条日志输出多次。
    if not logger.handlers:
        # StreamHandler 默认写入标准错误流，适合容器采集日志。
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)

    return logger

