namespace CsharpApp.Models;

/// <summary>
/// Generates geometric Brownian motion price steps from an injected RNG.
/// </summary>
public sealed class GbmPriceEngine
{
    private readonly Random _random;

    public GbmPriceEngine(Random random)
    {
        _random = random ?? throw new ArgumentNullException(nameof(random));
    }

    public double NextPrice(
        double currentPrice,
        double drift,
        double volatility,
        double deltaTime)
    {
        ValidateInputs(currentPrice, drift, volatility, deltaTime);

        // Random.NextDouble() is in [0, 1), so 1 - value is in (0, 1].
        // This keeps log(u1) finite in the Box-Muller transform.
        var u1 = 1.0 - _random.NextDouble();
        var u2 = _random.NextDouble();
        var normalSample =
            Math.Sqrt(-2.0 * Math.Log(u1)) * Math.Cos(2.0 * Math.PI * u2);

        var exponent =
            (drift - (volatility * volatility / 2.0)) * deltaTime
            + volatility * Math.Sqrt(deltaTime) * normalSample;
        var candidate = currentPrice * Math.Exp(exponent);

        // Floating-point GBM can underflow or overflow even though mathematical
        // GBM stays positive. Never let an invalid candidate enter the model.
        return double.IsFinite(candidate) && candidate > 0
            ? candidate
            : currentPrice;
    }

    private static void ValidateInputs(
        double currentPrice,
        double drift,
        double volatility,
        double deltaTime)
    {
        if (!double.IsFinite(currentPrice) || currentPrice <= 0)
        {
            throw new ArgumentOutOfRangeException(
                nameof(currentPrice),
                "Current price must be finite and positive.");
        }

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

        if (!double.IsFinite(deltaTime) || deltaTime <= 0)
        {
            throw new ArgumentOutOfRangeException(
                nameof(deltaTime),
                "Delta time must be finite and positive.");
        }
    }
}
