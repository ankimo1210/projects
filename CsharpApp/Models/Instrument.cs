namespace CsharpApp.Models;

/// <summary>
/// Numeric state for one offline instrument. This type has no WPF dependency.
/// </summary>
public sealed class Instrument
{
    public const int DefaultHistoryCapacity = 300;

    public Instrument(
        string symbol,
        double initialPrice,
        double drift,
        double volatility,
        int historyCapacity = DefaultHistoryCapacity)
    {
        if (string.IsNullOrWhiteSpace(symbol))
        {
            throw new ArgumentException("A symbol is required.", nameof(symbol));
        }

        ValidatePrice(initialPrice, nameof(initialPrice));

        if (!double.IsFinite(drift))
        {
            throw new ArgumentOutOfRangeException(nameof(drift), "Drift must be finite.");
        }

        if (!double.IsFinite(volatility) || volatility < 0)
        {
            throw new ArgumentOutOfRangeException(
                nameof(volatility),
                "Volatility must be finite and non-negative.");
        }

        Symbol = symbol;
        Price = initialPrice;
        PreviousPrice = initialPrice;
        Drift = drift;
        Volatility = volatility;
        History = new PriceHistoryBuffer(historyCapacity);
        History.Add(initialPrice);
    }

    public string Symbol { get; }

    public double Price { get; private set; }

    public double PreviousPrice { get; private set; }

    public double Drift { get; }

    public double Volatility { get; }

    public PriceHistoryBuffer History { get; }

    public void UpdatePrice(double price)
    {
        ValidatePrice(price, nameof(price));

        PreviousPrice = Price;
        Price = price;
        History.Add(price);
    }

    private static void ValidatePrice(double price, string parameterName)
    {
        if (!double.IsFinite(price) || price <= 0)
        {
            throw new ArgumentOutOfRangeException(
                parameterName,
                "A price must be finite and positive.");
        }
    }
}
