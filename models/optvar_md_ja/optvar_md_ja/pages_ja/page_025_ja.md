# ページ 025

![ページ 025](../assets/page_images/page-025.jpg)

## 原文OCRテキスト

```text
Morgan Stanley                                                                             Confidential


       + Volume control: we will implement volume controls at order, product and portfolio level for
         risk swung to AIM.
3.3.      Model    Inputs   and    Data

3.3.1      Data Sources:

The three main data sources are listed below.
       + Autohedger feed: The autohedger itself produces real-time portfolio risks in the book which
         are the input of the Opt-Var model.
       + Market Bus: Market Bus is an internal market data service. Autohedger subscribes to
         Market Bus to get the input covariance matrix that is calibrated offline and fed it into the
         Opt-Var model. It also gets the hedge ratios from Market Bus to convert the original bonds
         and futures positions to the hedge instrument space.
       + EOS TDA tables: EOS is an internal GUI where traders monitor and control parameters
         used in various applications. All the model parameters come from the TDA tables in EOS,
         except for the covariance matrix. We present the model parameters in details in section
         below.
3.3.2.     Observable    Inputs:

       « Initial position qo: The unhedged risks in PVO1        ($/bps in the US, €/bps in EU) in the
         hedge instrument space.
       + Alpha a € 4: Alpha signal in bps. At the moment, no alpha is used in EU, so a is zero. In
         the US, alpha is manually entered by bookrunners.
       + Internal client CRB orders (0;)icn: Marketable CRB orders submited by internal clients
         to the Central Risk Book. Client self buy and sells are already matched by the CRB swing
         engine which also does not transmit the non-marketable orders to the CRB optimizer. Internal
         CRB orders are sorted by submission times.
3.3.3      Model    Parameters:

       * Covariance matrix © ¢ R%*¢: Covariance matrix of the hedge instruments yield increments
         in bps’. In our case, we require the covariance matrix to be positive definite.
       * Cost C € R*: Linear part of the execution costs in bps.
       * Quadratic costs M € R®**4: Quadratic part of the execution cost in bps/PV01, a diagonal
         matrix.
       + Hedgeable risk limit H; € R_, H, € Ry: The minimum and maximum net unhedged
         portfolio risk in PVO1 that we are willing to hold. It means our net risk position is bounded
         between H; and Hy. The values chosen for Hj, H, are a business decision set by bookrunners.
         Bookrunners can decide to use symmetric hedgeable risk limit, in that case the input is only
         H, and by definition Hy = —Hy,. Otherwise they can decide to use possibly asymmetric
         hedgeable risk limit and in that case they input both Hj; and Hy. The implementation for
         asymmetric hedgeable risk limit is currently not put in production and bookrunners can only
         use the symmetric hedgeable risk limit.
130115: Opt-Var                                                                          Page 25 of 136

                         [git] « Branch: iropt-var@be27d1a = Release:   (2024-10-31)
```
