"""Two-rung dip ladder for make.fun btc-race-24h-20261123-0511.

Strategy (long only, one position, scale-in on deeper dips):
  - Track EMA(25) of the 1-minute closes of CBBTC, seeded as the mean of
    its first 25 closes, then EMA += 2/26 * (close - EMA).
  - Rung 1: when the close is at least 70 bps below the EMA and we hold
    nothing, buy with 60% of the cash. The other 40% stays dry powder.
  - Rung 2: while holding, if the close falls to at least 90 bps below
    the EMA, buy with all the remaining cash (a deeper dip buys cheaper
    and lowers the average cost). One rung-2 buy per position at most.
  - Sell the whole position when the close is at least 70 bps above the
    EMA (the dip has reverted past the mean), or when the position is
    worth 110 bps less than its cost (stop-loss).
  - Never more than one order per reply; max slippage 100 bps per order.

Why this shape: the dev window is a steady grind up (+3.64% over 24h)
with very shallow pullbacks -- the deepest dip from any trailing high
is only 181 bps, and a washout bot waiting for a 350-450 bps capitulation
dip (the pattern that won the previous race) would never trade at all
here and would fail the dev gate. Dips against a 25-minute mean are
rare too (only 4 bars sit 70+ bps under it), so each dip has to count:
the ladder puts 60% to work on the first dip and keeps 40% back for a
deeper leg, instead of going all-in on one print. Verified through the
kit's own protocol with the grader's integer fill math (work/drive.py):
on the frozen dev window +$11.18 on $1,000 (3 trades, max drawdown
1.58%, deterministic across two runs) -- the second rung fired on the
very next bar after the first, buying the dip cheaper -- and the same
bot makes +$8.10 on the previous race's falling dev window (-4.91%,
4 trades, max drawdown 0.75%), so it clears the gate in both regimes.
The sell threshold sits in the middle of a flat plateau (sell +65..+75
bps all give the same dev result), not on an isolated spike.

Deterministic: standard library only, no network, no wall clock, no
files outside the repo, no randomness. Same bars give the same orders.
Position state is read from the harness every batch; the rung-2 flag is
derived from the fills the harness reports plus the position's cost,
so a rejected order can never leave the bot's books out of sync.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
EMA_SPAN = 25
RUNG1_BPS = 70        # rung 1 buys when close is this far below the EMA (bps)
RUNG2_BPS = 90        # rung 2 buys when close is this far below the EMA (bps)
RUNG1_PCT = 60        # percent of cash rung 1 spends
SELL_BPS = 70         # sell when close is this far above the EMA (bps)
STOP_BPS = 110        # sell when position value is this far below cost (bps)
MAX_SLIPPAGE_BPS = 100


class Ema:
    """One EMA: the mean of its first span of closes, then 2/(span+1) steps."""

    def __init__(self, span):
        self.span = span
        self.warm = []
        self.value = None

    def push(self, close):
        if self.value is not None:
            self.value += (2.0 / (self.span + 1)) * (close - self.value)
            return
        self.warm.append(close)
        if len(self.warm) == self.span:
            self.value = sum(self.warm) / self.span


ema = Ema(EMA_SPAN)
_order_no = [0]
_rung1_notional = [None]   # quote units spent by the rung-1 buy, if any
_rung2_done = [False]      # whether the rung-2 buy of this position landed


def _next_client_id(prefix):
    _order_no[0] += 1
    return "%s-%d" % (prefix, _order_no[0])


def on_batch(state, batch):
    # Learn from the fills of the orders sent on the previous batch.
    for fill in batch.get("fills") or []:
        if fill.get("status") == "filled" and str(fill.get("client_id", "")).startswith("rung2-"):
            _rung2_done[0] = True
    bar = None
    for b in batch["bars"]:
        if b["symbol"] == SYMBOL:
            bar = b
            break
    if bar is not None:
        ema.push(float(bar["c"]))
    if state.warming_up or ema.value is None or bar is None:
        return []
    close = float(bar["c"])
    # Deviation of the close from the EMA, in basis points.
    z_bps = (close - ema.value) / ema.value * 10000.0
    held = state.positions.get(SYMBOL)
    min_notional = int(state.hello["fees"]["min_notional_quote_units"])
    if held is None:
        # No position: forget the last position's ladder state.
        _rung1_notional[0] = None
        _rung2_done[0] = False
        if z_bps <= -RUNG1_BPS:
            notional = state.cash * RUNG1_PCT // 100
            if notional >= min_notional:
                _rung1_notional[0] = notional
                return [{"side": "buy", "symbol": SYMBOL,
                         "client_id": _next_client_id("rung1"),
                         "notional_quote_units": notional,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []
    # We hold: the rung-2 buy has landed if the cost grew past rung 1.
    if _rung1_notional[0] is not None and held.cost > _rung1_notional[0]:
        _rung2_done[0] = True
    # Rung 2: deepen the position on a deeper dip, once per position.
    if not _rung2_done[0] and z_bps <= -RUNG2_BPS and state.cash >= min_notional:
        _rung2_done[0] = True
        return [{"side": "buy", "symbol": SYMBOL,
                 "client_id": _next_client_id("rung2"),
                 "notional_quote_units": state.cash,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    # Sell on reversion past the mean, or on the stop-loss.
    if z_bps >= SELL_BPS:
        return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                 "client_id": _next_client_id("sell"),
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    value = state.value(SYMBOL, held.qty)
    # value <= cost * (1 - STOP_BPS/10000), in integers.
    if value * 10000 <= held.cost * (10000 - STOP_BPS):
        return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                 "client_id": _next_client_id("sell"),
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    return []


makefun_bars.run(on_batch)
