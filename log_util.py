import logging
import watchtower
import os
from datetime import datetime

log_group = os.getenv("LOG_GROUP")
log_name=os.getenv("LOG_NAME")

def get_logger():
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:  
        stream_name = f"{log_name}-{datetime.now().strftime('%Y-%m-%d')}"
        handler = watchtower.CloudWatchLogHandler(
            log_group=log_group,
            stream_name=stream_name
        )
        logger.addHandler(handler)
        logger.addHandler(logging.StreamHandler())

    return logger
