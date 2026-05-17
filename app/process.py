from __future__ import annotations

import logging
import time

from app.config import get_settings
from app.db import ensure_schema, get_connection
from app.observability import configure_logging, log_event
from app.processing import (
    PROCESSOR_POLL_INTERVAL_SECONDS,
    ensure_configured_grid_tiers,
    process_once,
)

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(debug=settings.debug, log_format=settings.log_format)

    log_event(
        logger,
        logging.INFO,
        "signal_processor_starting",
        message="Starting Signal Atlas grid processor",
    )

    connection = get_connection(settings)
    ensure_schema(connection)
    if ensure_configured_grid_tiers(connection):
        log_event(
            logger,
            logging.INFO,
            "signal_processor_grid_rebuild_requested",
            message="Reset processed signal grid cells for configured map tiers",
        )

    while True:
        result = process_once(connection)
        if result.selected_measurements:
            log_event(
                logger,
                logging.INFO,
                "signal_processor_batch_processed",
                message="Processed cellular measurements into signal grid cells",
                selected_measurements=result.selected_measurements,
                eligible_measurements=result.eligible_measurements,
                touched_cells=result.touched_cells,
                last_measurement_id=result.last_measurement_id,
            )
            continue
        time.sleep(PROCESSOR_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
