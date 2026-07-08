import logging

from app.core.logging import configure_logging


def test_configure_logging_sets_level_and_avoids_duplicate_handlers() -> None:
    logger = logging.getLogger("tests.step3")
    logger.handlers.clear()

    configured = configure_logging(logger_name="tests.step3", level="DEBUG")
    configured_again = configure_logging(logger_name="tests.step3", level="DEBUG")

    assert configured is configured_again
    assert configured.level == logging.DEBUG
    assert len(configured.handlers) == 1
    assert configured.handlers[0].formatter is not None
