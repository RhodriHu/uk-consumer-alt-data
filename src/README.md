# UK Consumer Alt-Data Trading Strategy

A personal project building a systematic long-only equity strategy on UK consumer stocks using alternative data signals.

## Universe

- Greggs (GRG.L)
- Next (NXT.L)
- JD Sports (JD.L)
- Domino's Pizza UK (DOM.L)
- Wetherspoons (JDW.L)
- B&M European (BME.L)
- Marks & Spencer (MKS.L)

## Signals

- Google Trends search volume
- Weather deviations from seasonal norms
- ONS retail sales sector data

## Methodology

Weekly rebalancing, hold top-ranked stocks by composite signal score, equal weighting. Backtested over 3 years with realistic transaction costs, then paper-traded on Interactive Brokers.

## Status

In development - Week 1.