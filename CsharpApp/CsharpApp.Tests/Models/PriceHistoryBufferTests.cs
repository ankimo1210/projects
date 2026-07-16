using System.Collections.Specialized;
using CsharpApp.Models;

namespace CsharpApp.Tests.Models;

public sealed class PriceHistoryBufferTests
{
    [Fact]
    public void InstrumentStartsWithInitialPriceAndTracksPreviousPrice()
    {
        var instrument = new Instrument("TEST", 100.0, 0.001, 0.02);

        Assert.Equal([100.0], instrument.History);

        instrument.UpdatePrice(101.5);

        Assert.Equal(100.0, instrument.PreviousPrice);
        Assert.Equal(101.5, instrument.Price);
        Assert.Equal([100.0, 101.5], instrument.History);
    }

    [Fact]
    public void DropsOldestValueOnTheThreeHundredAndFirstAppend()
    {
        var history = new PriceHistoryBuffer(300);

        for (var price = 1; price <= 301; price++)
        {
            history.Add(price);
        }

        Assert.Equal(300, history.Count);
        Assert.Equal(2.0, history[0]);
        Assert.Equal(301.0, history[^1]);
        Assert.Equal(Enumerable.Range(2, 300).Select(value => (double)value), history);
    }

    [Fact]
    public void EmitsAddBeforeCapacityAndResetWhenLogicalIndicesShift()
    {
        var history = new PriceHistoryBuffer(2);
        var actions = new List<NotifyCollectionChangedAction>();
        history.CollectionChanged += (_, eventArgs) => actions.Add(eventArgs.Action);

        history.Add(10);
        history.Add(20);
        history.Add(30);

        Assert.Equal(
            [
                NotifyCollectionChangedAction.Add,
                NotifyCollectionChangedAction.Add,
                NotifyCollectionChangedAction.Reset,
            ],
            actions);
    }

    [Fact]
    public void RejectsInvalidCapacityAndPrices()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => new PriceHistoryBuffer(0));

        var history = new PriceHistoryBuffer(3);
        Assert.Throws<ArgumentOutOfRangeException>(() => history.Add(0));
        Assert.Throws<ArgumentOutOfRangeException>(() => history.Add(double.NaN));
    }
}
