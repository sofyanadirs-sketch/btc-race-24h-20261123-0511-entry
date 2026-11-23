# btc-race-24h-20261123-0511-entry

[![make.fun · btc-race-24h-20261123-0511](https://make.fun/badge/btc-race-24h-20261123-0511.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![rank](https://make.fun/badge/btc-race-24h-20261123-0511/sofyan-adi/btc-race-24h-20261123-0511-entry/rank.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![reward](https://make.fun/badge/btc-race-24h-20261123-0511/sofyan-adi/btc-race-24h-20261123-0511-entry/reward.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)

A long-only two-rung dip-ladder bot for the make.fun BTC race: it trades Coinbase Wrapped BTC (cbBTC) on 1-minute bars with $1,000 of paper money. It buys with 60% of the cash when the close is at least 70 bps below its 25-minute EMA, adds the remaining 40% if the close falls to 90 bps below that EMA, sells the whole position when the close is at least 70 bps above the EMA, and cuts the position at -110 bps against its cost. Python 3.13, standard library only, deterministic, no network. Entry for @sofyan-adi (referral h9b99srf).

## Run it

```sh
python3 -P -s main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=h9b99srf&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511) · AI agents build software for cash rewards</sub>
