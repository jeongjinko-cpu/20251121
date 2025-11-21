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
    --maturity 1.0
```

By default you will be prompted to enter a payoff expression in terms of the
terminal price `s` (for example, `max(s - 100, 0)` for a call or `max(100 - s,
0)` for a put).

To skip the prompt, pass the payoff directly:

```bash
python monte_carlo_option_pricing.py --spot 100 --rate 0.05 --volatility 0.2 \
    --maturity 1.0 --payoff "max(s - 100, 0)"
```

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
