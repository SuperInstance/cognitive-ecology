"""Research organisms: the panel and the discussion loop."""

from .discussion import Discussion, Transcript, next_round_number, slugify
from .panel import DEFAULT_PANEL, SYNTHESIZER, Participant, panel_for

__all__ = [
    "Discussion",
    "Transcript",
    "next_round_number",
    "slugify",
    "DEFAULT_PANEL",
    "SYNTHESIZER",
    "Participant",
    "panel_for",
]
