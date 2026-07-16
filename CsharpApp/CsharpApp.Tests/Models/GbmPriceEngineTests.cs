using CsharpApp.Models;

namespace CsharpApp.Tests.Models;

public sealed class GbmPriceEngineTests
{
    public static TheoryData<double, double> ConfiguredMotionParameters => new()
    {
        { 0.0005, 0.008 },
        { -0.0002, 0.012 },
        { 0.0010, 0.018 },
        { 0.0000, 0.025 },
        { 0.0015, 0.040 },
    };

    [Fact]
    public void SameSeedProducesTheSameSeries()
    {
        var first = new GbmPriceEngine(new Random(1729));
        var second = new GbmPriceEngine(new Random(1729));
        var firstPrice = 100.0;
        var secondPrice = 100.0;

        for (var step = 0; step < 500; step++)
        {
            firstPrice = first.NextPrice(firstPrice, 0.001, 0.02, 0.25);
            secondPrice = second.NextPrice(secondPrice, 0.001, 0.02, 0.25);

            Assert.Equal(firstPrice, secondPrice);
        }
    }

    [Theory]
    [MemberData(nameof(ConfiguredMotionParameters))]
    public void ConfiguredParametersStayFiniteAndPositive(
        double drift,
        double volatility)
    {
        var engine = new GbmPriceEngine(new Random(42));
        var price = 100.0;

        for (var step = 0; step < 10_000; step++)
        {
            price = engine.NextPrice(price, drift, volatility, 0.25);
            Assert.True(double.IsFinite(price));
            Assert.True(price > 0);
        }
    }

    [Fact]
    public void ZeroDriftAndVolatilityLeavePriceExactlyUnchanged()
    {
        var engine = new GbmPriceEngine(new Random(7));

        var result = engine.NextPrice(123.45, 0, 0, 0.25);

        Assert.Equal(123.45, result);
    }

    [Fact]
    public void InvalidInputsAreRejected()
    {
        var engine = new GbmPriceEngine(new Random(7));

        Assert.Throws<ArgumentOutOfRangeException>(
            () => engine.NextPrice(0, 0, 0.1, 0.25));
        Assert.Throws<ArgumentOutOfRangeException>(
            () => engine.NextPrice(double.NaN, 0, 0.1, 0.25));
        Assert.Throws<ArgumentOutOfRangeException>(
            () => engine.NextPrice(100, double.PositiveInfinity, 0.1, 0.25));
        Assert.Throws<ArgumentOutOfRangeException>(
            () => engine.NextPrice(100, 0, -0.1, 0.25));
        Assert.Throws<ArgumentOutOfRangeException>(
            () => engine.NextPrice(100, 0, 0.1, 0));
    }

    [Fact]
    public void NonFiniteCandidateFallsBackToLastValidPrice()
    {
        var engine = new GbmPriceEngine(new Random(7));

        var result = engine.NextPrice(100.0, double.MaxValue, 0, 1.0);

        Assert.Equal(100.0, result);
    }
}
