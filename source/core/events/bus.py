import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class Payload:
    """
    Shared state passed through the pipeline.
    Contains data and control flow flags for cancellation.
    """
    data: Dict[str, Any] = field(default_factory=dict)

    # Internal flags for cancellation state
    _cancel_cycle: bool = False
    _cancel_pipeline: bool = False

    def cancel_cycle(self):
        """Signals that remaining events in the current cycle should be skipped."""
        self._cancel_cycle = True

    def cancel_pipeline(self):
        """Signals that the entire pipeline should halt immediately."""
        self._cancel_pipeline = True
        self._cancel_cycle = True


@dataclass
class Event:
    """
    Base event class representing a single stage of processing.

    Args:
        callback:  Function with signature (payload: Payload) -> None.
                   Receives the shared payload object and may modify payload.data,
                   call payload.cancel_cycle(), or payload.cancel_pipeline().
        priority:  Integer 0–100. Higher values execute first. Core = 50.
                   Use >50 for pre-processing, <50 for post-processing.
        name:      Optional human-readable identifier for logging/debugging.
    """
    callback: Callable[[Payload], None]
    priority: int = 50
    name: str = ""

    def __post_init__(self):
        if not 0 <= self.priority <= 100:
            raise ValueError(
                f"Event priority must be between 0 and 100, got {self.priority}."
            )
        if not self.name:
            # Fall back to the callback's function name
            self.name = getattr(self.callback, "__name__", repr(self.callback))

    def __repr__(self):
        return f"Event(name={self.name!r}, priority={self.priority})"


class Cycle:
    """
    Represents a stage in the pipeline containing multiple sorted events.
    """
    def __init__(self, name: str, events: List[Event]):
        self.name: str = name
        self._events: List[Event] = events

    def run(self, payload: Payload) -> Payload:
        log.debug(f"Starting cycle: {self.name}")

        # Reset cycle cancellation flag at the start of each cycle
        payload._cancel_cycle = False

        for event in self._events:
            # Check for cancellation before running the next event
            if payload._cancel_cycle:
                log.debug(f"Cycle '{self.name}' cancelled. Skipping remaining events.")
                break

            log.debug(f"Running event: {event.name} (Priority: {event.priority})")

            try:
                event.callback(payload)
            except Exception as e:
                log.error(f"Error in event '{event.name}': {e}")
                # Re-raise to prevent the pipeline from silently failing
                raise

        return payload

    def add_event(self, event: Event):
        self._events.append(event)
        # Sort logic: Higher priority first (descending), then alphabetical name
        self._events.sort(key=lambda e: (-e.priority, e.name))


class EventBus:
    """
    Manages the overall pipeline execution, cycles, and plugin registration.
    """
    def __init__(self):
        # Using a dict allows O(1) lookup for plugins adding events by cycle name
        self._cycles: Dict[str, Cycle] = {}

    def add_cycle(self, cycle: Cycle):
        """Registers a core cycle into the pipeline."""
        if cycle.name in self._cycles:
            log.warning(f"Cycle '{cycle.name}' already exists. Overwriting.")
        self._cycles[cycle.name] = cycle

    def add_event(self, cycle: str, priority: int, callback: Callable[[Payload], None], name: str = ""):
        """
        Allows plugins to inject events into specific cycles by name.
        """
        new_event = Event(callback=callback, priority=priority, name=name)
        if cycle not in self._cycles:
            log.info(f"Cycle '{cycle}' not found. Creating it dynamically.")
            self.add_cycle(Cycle(cycle, [new_event]))

        self._cycles[cycle].add_event(new_event)

    def run(self, initial_data: Optional[Dict[str, Any]] = None) -> Payload:
        """
        Executes the pipeline sequentially.
        """
        payload = Payload(data=initial_data or {})
        log.info("Starting pipeline execution.")

        for cycle_name, cycle in self._cycles.items():
            # Check global pipeline cancellation before entering the next cycle
            if payload._cancel_pipeline:
                log.info("Pipeline cancelled. Skipping remaining cycles.")
                break

            payload = cycle.run(payload)

        log.info("Pipeline execution finished.")
        return payload