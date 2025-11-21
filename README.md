# Binomial Option Pricing (20251121)

This repository contains a minimal Python implementation of the binomial option
pricing model using the Cox-Ross-Rubinstein lattice.

## Usage

1. Ensure you have Python 3.10+ available.
2. Run the demo script to see a sample European call price:

```bash
python binomial_option_pricing.py
```

To estimate an option price with Monte Carlo simulation and a custom payoff,
run:

```bash
python monte_carlo_option_pricing.py --spot 100 --rate 0.05 --volatility 0.2 \
    --maturity 1.0 --payoff "max(s - 100, 0)"
```

## Web Monte Carlo calculator

A lightweight Flask server is included so you can try different payoff
structures interactively:

```bash
pip install flask  # if Flask is not already available
python web_option_calculator.py
```

Then open http://127.0.0.1:5000/ in your browser. You can:

* Enter market parameters (spot, rate, dividend yield, volatility, maturity).
* Choose the number of Monte Carlo simulations and an optional RNG seed.
* Provide constants such as strike ``K`` or barrier ``B`` and any additional
  JSON constants (e.g., ``{"rebate": 2.5, "cap": 120}``).
* Write a payoff expression using ``s``, ``ST``, or ``S_T`` for the terminal
  price and your constants. Examples: ``max(S_T - K, 0)`` (vanilla call),
  ``max(B - S_T, 0) * (S_T < B)`` (simple down-and-in payoff), or
  ``min(max(S_T - K, 0), cap)`` when paired with a ``cap`` constant.

## API

The core pricing logic is available via the `price_option` function, which accepts
an `OptionSpec` dataclass instance:

```python
from binomial_option_pricing import OptionSpec, price_option

spec = OptionSpec(
    spot=100,
    strike=100,
    maturity=1.0,
    rate=0.05,
    volatility=0.2,
    steps=200,
    option_type="call",  # or "put"
    exercise="european",  # or "american"
    dividend_yield=0.0,
)

price = price_option(spec)
print(price)
```

European and American exercise styles are supported, along with continuous dividend
yields. Error handling guards against invalid parameter combinations (e.g.,
non-positive steps or probabilities outside the risk-neutral interval).
