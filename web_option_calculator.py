"""Simple Flask web UI for Monte Carlo option pricing with custom payoffs."""
from __future__ import annotations

import json
from typing import Any

from flask import Flask, render_template_string, request, url_for

from monte_carlo_option_pricing import compile_payoff, monte_carlo_price

app = Flask(__name__)

DEFAULT_FORM = {
    "spot": 100.0,
    "rate": 0.05,
    "dividend_yield": 0.0,
    "volatility": 0.2,
    "maturity": 1.0,
    "simulations": 10000,
    "strike": 100.0,
    "barrier": "",
    "custom_context": "{\n  \"rebate\": 0.0\n}",
    "payoff": "max(S_T - K, 0)",
    "seed": "",
}

PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Monte Carlo Option Calculator</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2rem auto; max-width: 900px; }
        h1 { margin-bottom: 0.2rem; }
        .note { color: #444; margin-top: 0; }
        form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem 1.5rem; }
        label { font-weight: bold; display: block; margin-bottom: 0.4rem; }
        input, textarea { width: 100%; padding: 0.4rem; font-size: 1rem; }
        textarea { min-height: 6rem; }
        .full { grid-column: span 2; }
        .result { background: #f5f5f5; padding: 1rem; border-radius: 8px; margin-top: 1rem; }
        .error { color: #b00020; font-weight: bold; }
        button { padding: 0.7rem 1.2rem; font-size: 1rem; cursor: pointer; }
        code { background: #eee; padding: 0 0.2rem; }
    </style>
</head>
<body>
    <h1>Monte Carlo Option Calculator</h1>
    <p class="note">Enter market parameters and a payoff expression to price options with Monte Carlo simulation.</p>

    {% if error %}
        <div class="result error">{{ error }}</div>
    {% endif %}

    {% if price %}
        <div class="result">Estimated price: <strong>{{ price }}</strong></div>
    {% endif %}

    <form method="post" action="{{ url_for('index') }}">
        <div>
            <label for="spot">Spot (S0)</label>
            <input id="spot" name="spot" type="number" step="any" value="{{ form_values.spot }}" required>
        </div>
        <div>
            <label for="rate">Risk-free rate (r)</label>
            <input id="rate" name="rate" type="number" step="any" value="{{ form_values.rate }}" required>
        </div>
        <div>
            <label for="dividend_yield">Dividend yield (q)</label>
            <input id="dividend_yield" name="dividend_yield" type="number" step="any" value="{{ form_values.dividend_yield }}" required>
        </div>
        <div>
            <label for="volatility">Volatility (σ)</label>
            <input id="volatility" name="volatility" type="number" step="any" value="{{ form_values.volatility }}" required>
        </div>
        <div>
            <label for="maturity">Maturity (years)</label>
            <input id="maturity" name="maturity" type="number" step="any" value="{{ form_values.maturity }}" required>
        </div>
        <div>
            <label for="simulations">Simulations</label>
            <input id="simulations" name="simulations" type="number" step="1" min="1" value="{{ form_values.simulations }}" required>
        </div>
        <div>
            <label for="strike">Strike (K, optional)</label>
            <input id="strike" name="strike" type="number" step="any" value="{{ form_values.strike }}">
        </div>
        <div>
            <label for="barrier">Barrier level (B, optional)</label>
            <input id="barrier" name="barrier" type="number" step="any" value="{{ form_values.barrier }}">
        </div>
        <div class="full">
            <label for="payoff">Payoff expression</label>
            <textarea id="payoff" name="payoff" required>{{ form_values.payoff }}</textarea>
            <p class="note">Use any of the variables <code>s</code>, <code>ST</code>, or <code>S_T</code> for the terminal price, plus constants you set below (e.g. <code>K</code>, <code>B</code>, <code>rebate</code>). Example: <code>max(S_T - K, 0)</code></p>
        </div>
        <div class="full">
            <label for="custom_context">Extra constants (JSON object)</label>
            <textarea id="custom_context" name="custom_context">{{ form_values.custom_context }}</textarea>
            <p class="note">Provide any additional constants your payoff uses. Example: <code>{"rebate": 2.5, "cap": 120}</code></p>
        </div>
        <div>
            <label for="seed">Random seed (optional)</label>
            <input id="seed" name="seed" type="number" step="1" value="{{ form_values.seed }}">
        </div>
        <div class="full">
            <button type="submit">Calculate</button>
        </div>
    </form>

    <div class="result">
        <strong>Tips:</strong>
        <ul>
            <li>Terminal price aliases: <code>s</code>, <code>ST</code>, <code>S_T</code>.</li>
            <li>Constants available automatically: <code>K</code> (strike), <code>B</code> (barrier, if set), and anything supplied in the JSON box.</li>
            <li>Math helpers: <code>exp</code>, <code>log</code>, <code>sqrt</code>, <code>sin</code>, <code>cos</code>, <code>tan</code>, <code>fabs</code>, <code>pi</code>, <code>e</code>, <code>erf</code>, <code>erfc</code>, <code>max</code>, <code>min</code>.</li>
        </ul>
    </div>
</body>
</html>
"""


def _to_float(value: str, *, field: str) -> float:
    try:
        return float(value)
    except ValueError as exc:  # pragma: no cover - interactive helper
        raise ValueError(f"{field} must be numeric") from exc


def _parse_constants(raw: str) -> dict[str, float]:
    if not raw.strip():
        return {}

    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - interactive helper
        raise ValueError(f"Could not parse JSON constants: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Constants JSON must decode to an object/dictionary")

    constants: dict[str, float] = {}
    for key, value in data.items():
        constants[str(key)] = float(value)
    return constants


@app.route("/", methods=["GET", "POST"])
def index():
    form_values = DEFAULT_FORM.copy()
    error: str | None = None
    price: str | None = None

    if request.method == "POST":
        try:
            form_values.update({
                "spot": _to_float(request.form.get("spot", ""), field="Spot"),
                "rate": _to_float(request.form.get("rate", ""), field="Rate"),
                "dividend_yield": _to_float(request.form.get("dividend_yield", ""), field="Dividend yield"),
                "volatility": _to_float(request.form.get("volatility", ""), field="Volatility"),
                "maturity": _to_float(request.form.get("maturity", ""), field="Maturity"),
                "simulations": int(_to_float(request.form.get("simulations", ""), field="Simulations")),
                "strike": _to_float(request.form.get("strike", DEFAULT_FORM["strike"]), field="Strike"),
                "barrier": request.form.get("barrier", ""),
                "custom_context": request.form.get("custom_context", DEFAULT_FORM["custom_context"]),
                "payoff": request.form.get("payoff", DEFAULT_FORM["payoff"]),
                "seed": request.form.get("seed", ""),
            })

            barrier_value = float(form_values["barrier"]) if str(form_values["barrier"]).strip() else None
            seed_value = int(form_values["seed"]) if str(form_values["seed"]).strip() else None

            constants = _parse_constants(str(form_values["custom_context"]))
            constants.update({"K": float(form_values["strike"])} if str(form_values["strike"]).strip() else {})
            if barrier_value is not None:
                constants["B"] = barrier_value

            payoff_fn = compile_payoff(
                str(form_values["payoff"]),
                variables={"s", "ST", "S_T"},
                context=constants,
            )

            price_value = monte_carlo_price(
                spot=float(form_values["spot"]),
                rate=float(form_values["rate"]),
                volatility=float(form_values["volatility"]),
                maturity=float(form_values["maturity"]),
                dividend_yield=float(form_values["dividend_yield"]),
                simulations=int(form_values["simulations"]),
                payoff=payoff_fn,
                seed=seed_value,
            )
            price = f"{price_value:.4f}"
        except Exception as exc:  # pragma: no cover - interactive handler
            error = str(exc)

    return render_template_string(
        PAGE,
        form_values=form_values,
        error=error,
        price=price,
    )


def create_app() -> Flask:
    """Factory for unit tests or external servers."""
    return app


if __name__ == "__main__":  # pragma: no cover - manual run helper
    app.run(debug=True)
