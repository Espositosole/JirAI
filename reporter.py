from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class TestStepResult:
    """Unified result object for executed test steps."""

    step: Dict[str, Any]
    status: str
    error: Optional[str] = None
    screenshot: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dictionary representation."""
        return asdict(self)
