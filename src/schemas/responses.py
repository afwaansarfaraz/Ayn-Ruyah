"""Standardized API response schemas and data structures."""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass
class DiagnosticResult:
    """Diagnostic response contract returned by the AI screening pipeline."""
    grade: int
    result: str
    severity: str
    confidence: float
    color: str
    recommendation: str
    probabilities: Dict[str, float]
    heatmap: str
    demo_mode: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to JSON serializable dictionary matching frontend schema."""
        return {
            "grade": self.grade,
            "result": self.result,
            "severity": self.severity,
            "confidence": round(self.confidence, 2),
            "color": self.color,
            "recommendation": self.recommendation,
            "probabilities": self.probabilities,
            "heatmap": self.heatmap,
            "demo_mode": self.demo_mode,
        }


@dataclass
class HealthStatus:
    """System health check response contract."""
    status: str
    model_loaded: bool
    model: str
    classes: int
    device: str
    image_size: int
    gradcam: str
    trained_on: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

