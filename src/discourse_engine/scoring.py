"""Calibrated scoring model for assumption and rhetorical detection.

Replaces arbitrary confidence percentages with weighted linear model:
  score = w1*modal_strength + w2*causal_dependency + w3*absence_of_support + w4*normative_density
Normalized to [0, 1].
"""

# Weights for assumption scoring (Step 4)
W_MODAL_STRENGTH = 0.4
W_CAUSAL_DEPENDENCY = 0.3
W_ABSENCE_OF_SUPPORT = 0.2
W_NORMATIVE_DENSITY = 0.1


def assumption_score(
    modal_strength: float,
    causal_dependency: float,
    absence_of_support: float,
    normative_density: float,
) -> float:
    """
    Calibrated assumption score.
    All inputs in [0, 1]. Output in [0, 1].
    """
    raw = (
        W_MODAL_STRENGTH * modal_strength
        + W_CAUSAL_DEPENDENCY * causal_dependency
        + W_ABSENCE_OF_SUPPORT * absence_of_support
        + W_NORMATIVE_DENSITY * normative_density
    )
    return min(max(raw, 0.0), 1.0)


def modal_strength_from_type(detection_type: str) -> float:
    """Map detection type to modal/structural strength component."""
    # Higher = stronger structural signal
    mapping = {
        "loaded_question": 0.95,
        "epistemic_shortcut": 0.85,
        "factive": 0.80,
        "necessity_modal_outcome": 0.75,
        "without_x_y": 0.72,
        "conclusion_marker": 0.70,
        "repetition": 0.68,
        "vague_authority": 0.75,
        "implicative": 0.62,
        "change_of_state": 0.60,
        "value_loaded": 0.55,
        "causal": 0.58,
        "universal": 0.78,
    }
    return mapping.get(detection_type, 0.5)


def absence_of_support(has_justification_nearby: bool) -> float:
    """Higher when no evidence/justification in context."""
    return 0.9 if not has_justification_nearby else 0.3
