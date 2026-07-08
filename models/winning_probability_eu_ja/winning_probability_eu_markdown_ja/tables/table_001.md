# Table 1 - Economic information received by dealers

Source: page 8. The original table is rotated in the PDF; see `../assets/derived/page_008_table_rotated.png` for a readable visual copy.

Dealer 1 always wins. Notation: `dlr` = dealer, `ER` = `ExecutionReport`, `QR` = `QuoteResponse`.

## Scenario 1

Price levels: `a`: dealers 1, 2, 3; `b`: dealer 4.

| Dealer | TW msg | TW cover-px | TW doneAway | TW coverStatus | MS inquiryState | MS tradeState | MS coverPrice |
|---|---|---:|---|---|---|---|---:|
| dlr 1 | ER | a | - | - | Done | DoneTied | a |
| dlr 2 | QR | - | tied | no | DoneAway | TiedTradedAway | a |
| dlr 3 | QR | - | tied | no | DoneAway | TiedTradedAway | a |
| dlr 4 | QR | - | yes | no | DoneAway | TradedAway | n/a |

## Scenario 2

Price levels: `a`: dealers 1, 2; `b`: dealers 3, 4.

| Dealer | TW msg | TW cover-px | TW doneAway | TW coverStatus | MS inquiryState | MS tradeState | MS coverPrice |
|---|---|---:|---|---|---|---|---:|
| dlr 1 | ER | a | - | - | Done | DoneTied | a |
| dlr 2 | QR | - | tied | no | DoneAway | TiedTradedAway | a |
| dlr 3 | QR | - | yes | no | DoneAway | TradedAway | n/a |
| dlr 4 | QR | - | yes | no | DoneAway | TradedAway | n/a |

## Scenario 3

Price levels: `a`: dealer 1; `b`: dealers 2, 3; `c`: dealer 4.

| Dealer | TW msg | TW cover-px | TW doneAway | TW coverStatus | MS inquiryState | MS tradeState | MS coverPrice |
|---|---|---:|---|---|---|---|---:|
| dlr 1 | ER | b | - | - | Done | - | b |
| dlr 2 | QR | - | yes | tied | DoneAway | CoverTied | b |
| dlr 3 | QR | - | yes | tied | DoneAway | CoverTied | b |
| dlr 4 | QR | - | yes | no | DoneAway | TradedAway | n/a |

## Scenario 4

Price levels: `a`: dealer 1; `b`: dealer 2; `c`: dealers 3, 4.

| Dealer | TW msg | TW cover-px | TW doneAway | TW coverStatus | MS inquiryState | MS tradeState | MS coverPrice |
|---|---|---:|---|---|---|---|---:|
| dlr 1 | ER | b | - | - | Done | - | b |
| dlr 2 | QR | - | yes | yes | DoneAway | Covered | b |
| dlr 3 | QR | - | yes | no | DoneAway | TradedAway | n/a |
| dlr 4 | QR | - | yes | no | DoneAway | TradedAway | n/a |

Caption: The economic information received by dealers in a four-way auction, under four pricing scenarios. All dealer prices are on the bid side; the customer is looking to sell.
