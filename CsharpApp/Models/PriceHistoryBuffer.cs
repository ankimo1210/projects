using System.Collections;
using System.Collections.Specialized;

namespace CsharpApp.Models;

/// <summary>
/// A fixed-capacity price history in chronological order.
/// </summary>
public sealed class PriceHistoryBuffer : IReadOnlyList<double>, INotifyCollectionChanged
{
    private readonly double[] _buffer;
    private int _start;

    public PriceHistoryBuffer(int capacity)
    {
        if (capacity <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(capacity), "Capacity must be positive.");
        }

        _buffer = new double[capacity];
    }

    public event NotifyCollectionChangedEventHandler? CollectionChanged;

    public int Capacity => _buffer.Length;

    public int Count { get; private set; }

    public double this[int index]
    {
        get
        {
            if ((uint)index >= (uint)Count)
            {
                throw new ArgumentOutOfRangeException(nameof(index));
            }

            return _buffer[PhysicalIndex(index)];
        }
    }

    public void Add(double value)
    {
        if (!double.IsFinite(value) || value <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(value), "A price must be finite and positive.");
        }

        if (Count < Capacity)
        {
            _buffer[PhysicalIndex(Count)] = value;
            Count++;
            CollectionChanged?.Invoke(
                this,
                new NotifyCollectionChangedEventArgs(
                    NotifyCollectionChangedAction.Add,
                    value,
                    Count - 1));
            return;
        }

        _buffer[_start] = value;
        _start = (_start + 1) % Capacity;

        // Logical indices all shift after the oldest value is replaced.
        CollectionChanged?.Invoke(
            this,
            new NotifyCollectionChangedEventArgs(NotifyCollectionChangedAction.Reset));
    }

    public IEnumerator<double> GetEnumerator()
    {
        for (var index = 0; index < Count; index++)
        {
            yield return this[index];
        }
    }

    IEnumerator IEnumerable.GetEnumerator() => GetEnumerator();

    private int PhysicalIndex(int logicalIndex) => (_start + logicalIndex) % Capacity;
}
