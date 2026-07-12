import logging


LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(logger_name: str = "yu_ai_agent", level: str = "INFO") -> logging.Logger:
    # logging.getLogger 会按名称复用 Logger；同名调用不会重复创建实例。
    logger = logging.getLogger(logger_name)
    logger.setLevel(level.upper())
    logger.propagate = False

    # 防止应用重复初始化时不断追加 Handler，造成同一条日志输出多次。
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)

    return logger

