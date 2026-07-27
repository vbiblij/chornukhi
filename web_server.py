from __future__ import annotations
import threading
from core.process import Process
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from core.event_bus import EventBus

# Suppress Flask's default startup messages
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)



        # Daemon thread will be terminated automatically.
