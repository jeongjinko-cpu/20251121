"""
Binomial option pricing model implementation using the Cox-Ross-Rubinstein lattice.

The implementation supports European and American call/put options with an optional
continuous dividend yield. It exposes a single function `price_option` that returns
the risk-neutral price given market inputs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

OptionType = Literal["call", "put"]
ExerciseType = Literal["european", "american"]


@dataclass(frozen=True)
class OptionSpec:
    """Option details required for binomial pricing."""

    spot: float
    strike: float
    maturity: float
    rate: float
    volatility: float
    steps: int
    option_type: OptionType = "call"
    exercise: ExerciseType = "european"
    dividend_yield: float = 0.0

    def __post_init__(self) -> None:
        if self.steps <= 0:
            raise ValueError("steps must be a positive integer")
        if self.maturity <= 0:
            raise ValueError("maturity must be positive (in years)")
        if self.volatility < 0:
            raise ValueError("volatility cannot be negative")
        if self.dividend_yield < 0:
            raise ValueError("dividend_yield cannot be negative")
        if self.option_type not in ("call", "put"):
            raise ValueError("option_type must be 'call' or 'put'")
        if self.exercise not in ("european", "american"):
            raise ValueError("exercise must be 'european' or 'american'")


def _compute_parameters(spec: OptionSpec) -> tuple[float, float, float, float, float]:
    dt = spec.maturity / spec.steps
    up = math.exp(spec.volatility * math.sqrt(dt))
    down = 1.0 / up
    growth = math.exp((spec.rate - spec.dividend_yield) * dt)
    prob = (growth - down) / (up - down)

    if not 0.0 <= prob <= 1.0:
        raise ValueError(
            "The computed risk-neutral probability is outside [0, 1]. "
            "Check the step count or input parameters."
        )

    discount = math.exp(-spec.rate * dt)
    return dt, up, down, prob, discount


def price_option(spec: OptionSpec) -> float:
    """Price an option using a Cox-Ross-Rubinstein binomial tree.

    Args:
        spec: Inputs describing the option and market parameters.

    Returns:
        The option price under the risk-neutral measure.
    """
    _dt, up, down, prob, discount = _compute_parameters(spec)

    # Terminal asset prices at maturity
    prices = [
        spec.spot * (up ** j) * (down ** (spec.steps - j))
        for j in range(spec.steps + 1)
    ]

    if spec.option_type == "call":
        values = [max(price - spec.strike, 0.0) for price in prices]
    else:
        values = [max(spec.strike - price, 0.0) for price in prices]

    american = spec.exercise == "american"

    for step in reversed(range(spec.steps)):
        next_values = []
        for j in range(step + 1):
            continuation = discount * (prob * values[j + 1] + (1 - prob) * values[j])
            if american:
                spot = spec.spot * (up ** j) * (down ** (step - j))
                exercise_value = (
                    max(spot - spec.strike, 0.0)
                    if spec.option_type == "call"
                    else max(spec.strike - spot, 0.0)
                )
                next_values.append(max(continuation, exercise_value))
            else:
                next_values.append(continuation)
        values = next_values

    return values[0]


def demo() -> None:
    """Demonstrate pricing with a simple example."""
    spec = OptionSpec(
        spot=100,
        strike=100,
        maturity=1.0,
        rate=0.05,
        volatility=0.2,
        steps=200,
        option_type="call",
        exercise="european",
    )
    price = price_option(spec)
    print(f"European call price: {price:.4f}")


if __name__ == "__main__":
    demo()
