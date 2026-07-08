# ページ 024

![ページ 024](../assets/page_images/page-024.jpg)

## 原文OCRテキスト

```text
Morgan Stanley                                                                              Confidential


The set B of constraints is made of client constraints applied to AIM:
   + Decreasing AIM bucket risk:
                                                    N
                            min(q’,0)
                               <q? + Sou} < max(q’,0) Vj E1,--- ,d.
                                                i=l

   + Decreasing AIM net risk:
                                   d                d     N               d
                           min (0,0) <y@+h™) <max (P90).
                                                =

The desk and strats can choose to either use set A or set B of constraints.

   The admissible set is always non-empty because zero always verifies the constraints. In partic-
ular the constraints are never incompatible. Existence and uniqueness still follow from the same
reasoning as previously.

CRB    Swing      Engine The CRB       swing engine collects the internal client CRB   orders, reads the
model parameters and inputs. It also nets client self buys and sell CRB orders on the same product
and checks which CRB orders are marketable. At a frequency which is a strats controlled param-
eter, the CRB swing engine calls the CRB optimizer which determines the optimal quantities to
fill for each marketable order. The swing engine eventually fills these CRB orders and books the
risk between the internal client account and eRates accounts with the swing trade mechanism. It
also sends a fast fill to the eRates book. This process is not part of the Autohedger algo and does
not interact directly with it at the moment. The position q are read from filter. The CRB opti-
mizer will be called at a fixed frequency, which is a strats chosen parameter of the CRB swing engine.

   Associated controls:
   + Internal client CRB orders. They must be of market or limit type. TimeInForce must be Day.
     Account must be valid and configured. The swing engine must be enabled. Product needs to
     be supported. Product dpdy must be valid. If these conditions are not met the CRB orders
     are rejected or cancelled.
   + Fills. Fill price cannot be NaN. Dpdy must be valid.
   + Inputs. The controls on the parameters are mentioned in Sectioi            For the position risk
     input, if AIM is not eligible, we take zero as the position and we use the set B of constraints
     for AIM. It means CRB swing engine will not change AIM risk (thanks to the bucket risk
     constraint) and can only swing risk directly between clients, with ATM in the middle.
   + The CRB swing engine will discard CRB optimizer outputs if the portfolio position has moved
     by more than a threshold since the start of the optimization.
   + The CRB optimizer will only be able to change AIM risk if the Autohedger is not actively
     hedging. The CRB swing engine will check the table RiskHedging in filter, and replace AIM
     risk by a zero portfolio if the Autohedger is hedging (one of the hedge values is non zero). In
     that case we use the set B of constraints for ATM to make sure CRB does not change AIM
     risk (thanks to the bucket risk constraint). But risk can still be swung between clients. If the
     Autohedger started to hedge during the CRB optimization we block any fill and swings.
130115: Opt-Var                                                                           Page 24 of 136

                       [git] « Branch: iropt-var@be27d1a = Release:   (2024-10-31)
```
