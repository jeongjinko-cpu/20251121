"""Monte Carlo option pricing with user-provided payoff expressions."""
from __future__ import annotations

import argparse
import math
import random
import ast
from typing import Callable


_ALLOWED_NAMES = {
    name: getattr(math, name)
    for name in (
        "exp",
        "log",
        "sqrt",
        "sin",
        "cos",
        "tan",
        "fabs",
        "pi",
        "e",
        "erf",
        "erfc",
    )
}
_ALLOWED_NAMES.update({
    "max": max,
    "min": min,
})


class _SafeExpressionEvaluator(ast.NodeVisitor):
    """Safely compile a mathematical expression of one variable `s`.

    Only a restricted subset of Python expressions is allowed to keep evaluation
    safe. Supported operations include basic arithmetic, power, and selected
    math functions (see `_ALLOWED_NAMES`).
    """

    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Load,
        ast.Name,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Mod,
        ast.USub,
        ast.UAdd,
        ast.Call,
        ast.Constant,
        ast.FloorDiv,
    )

    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit(self, node):  # type: ignore[override]
        if not isinstance(node, self.allowed_nodes):
            raise ValueError(f"Disallowed expression component: {ast.dump(node)}")
        return super().visit(node)

    def visit_Name(self, node: ast.Name):
        if node.id != "s" and node.id not in _ALLOWED_NAMES:
            raise ValueError(f"Only variable 's' and math functions are allowed, got {node.id!r}")
        self.names.add(node.id)

    def visit_Call(self, node: ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_NAMES:
            raise ValueError("Only simple calls to allowed math functions are permitted")
        for arg in node.args:
            self.visit(arg)
        for keyword in node.keywords:
            self.visit(keyword.value)


def compile_payoff(expression: str) -> Callable[[float], float]:
    """Compile a payoff expression into a callable.

    The expression should be a valid Python arithmetic expression in terms of the
    variable `s`, representing the terminal asset price. For example:

    * ``max(s - 100, 0)`` for a call option with strike 100
    * ``max(100 - s, 0)`` for a put option with strike 100

    Math helpers from :mod:`math` such as ``exp`` and ``sqrt`` are available.
    """

    tree = ast.parse(expression, mode="eval")
    _SafeExpressionEvaluator().visit(tree)
    compiled = compile(tree, filename="<payoff>", mode="eval")

    def payoff(s: float) -> float:
        return float(eval(compiled, {"__builtins__": {}}, {"s": s, **_ALLOWED_NAMES}))

    return payoff


def monte_carlo_price(
    *,
    spot: float,
    rate: float,
    volatility: float,
    maturity: float,
    dividend_yield: float,
    simulations: int,
    payoff: Callable[[float], float],
    seed: int | None = None,
) -> float:
    """Estimate an option price via Monte Carlo simulation.

    A geometric Brownian motion is simulated under the risk-neutral measure.
    Only the terminal asset price is required, making this suitable for
    European-style payoffs that depend on ``S_T``.
    """

    if simulations <= 0:
        raise ValueError("simulations must be positive")
    if maturity <= 0:
        raise ValueError("maturity must be positive")
    if volatility < 0:
        raise ValueError("volatility cannot be negative")

    rng = random.Random(seed)
    drift = (rate - dividend_yield - 0.5 * volatility * volatility) * maturity
    diffusion = volatility * math.sqrt(maturity)
    discount = math.exp(-rate * maturity)

    payoff_sum = 0.0
    for _ in range(simulations):
        z = rng.gauss(0.0, 1.0)
        s_t = spot * math.exp(drift + diffusion * z)
        payoff_sum += payoff(s_t)

    return discount * payoff_sum / simulations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monte Carlo option pricing with user-defined payoff expressions",
    )
    parser.add_argument("--spot", type=float, required=True, help="Current underlying price")
    parser.add_argument("--rate", type=float, required=True, help="Risk-free rate (annualized)")
    parser.add_argument("--volatility", type=float, required=True, help="Volatility (annualized)")
    parser.add_argument("--maturity", type=float, required=True, help="Time to maturity in years")
    parser.add_argument(
        "--dividend-yield", type=float, default=0.0, help="Continuous dividend yield (annualized)"
    )
    parser.add_argument(
        "--simulations", type=int, default=10000, help="Number of Monte Carlo paths"
    )
    parser.add_argument(
        "--payoff",
        type=str,
        default=None,
        help=(
            "Payoff expression in variable 's' (terminal price). Example: "
            "'max(s - 100, 0)' for a call, 'max(100 - s, 0)' for a put. "
            "If omitted, the script will prompt for it interactively."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional RNG seed for reproducible results",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payoff_expression = args.payoff or input(
        "Payoff expression in variable 's' (e.g., max(s - 100, 0) for a call): "
    ).strip()
    if not payoff_expression:
        raise SystemExit("A payoff expression is required to run the simulation.")

    payoff_fn = compile_payoff(payoff_expression)
    price = monte_carlo_price(
        spot=args.spot,
        rate=args.rate,
        volatility=args.volatility,
        maturity=args.maturity,
        dividend_yield=args.dividend_yield,
        simulations=args.simulations,
        payoff=payoff_fn,
        seed=args.seed,
    )
    print(f"Estimated option price: {price:.4f}")


if __name__ == "__main__":
    main()
