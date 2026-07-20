using System.Collections.ObjectModel;
using System.Windows.Input;
using System.Windows.Threading;
using CsharpApp.Models;

namespace CsharpApp.ViewModels;

public sealed class MainViewModel : ViewModelBase, IDisposable
{
    public const int MinimumIntervalMs = 100;
    public const int MaximumIntervalMs = 1_000;
    public const int DefaultIntervalMs = 250;

    private readonly DispatcherTimer _timer;
    private readonly GbmPriceEngine _priceEngine;
    private readonly RelayCommand _startCommand;
    private readonly RelayCommand _pauseCommand;
    private TickerViewModel? _selectedInstrument;
    private bool _isRunning;
    private bool _isDisposed;
    private int _updateIntervalMs = DefaultIntervalMs;

    public MainViewModel()
        : this(new Random())
    {
    }

    internal MainViewModel(Random random)
    {
        _priceEngine = new GbmPriceEngine(random);
        Instruments = new ObservableCollection<TickerViewModel>
        {
            CreateInstrument("ALPHA", 100.00, 0.0005, 0.008),
            CreateInstrument("BRAVO", 250.00, -0.0002, 0.012),
            CreateInstrument("CHARLIE", 75.00, 0.0010, 0.018),
            CreateInstrument("DELTA", 40.00, 0.0000, 0.025),
            CreateInstrument("NOVA-X", 1_000.00, 0.0015, 0.040),
        };

        _selectedInstrument = Instruments[0];
        _startCommand = new RelayCommand(Start, () => !IsRunning);
        _pauseCommand = new RelayCommand(Pause, () => IsRunning);

        _timer = new DispatcherTimer(DispatcherPriority.Background)
        {
            Interval = TimeSpan.FromMilliseconds(UpdateIntervalMs),
        };
        _timer.Tick += OnTimerTick;

        Start();
    }

    public ObservableCollection<TickerViewModel> Instruments { get; }

    public TickerViewModel? SelectedInstrument
    {
        get => _selectedInstrument;
        set => SetProperty(ref _selectedInstrument, value);
    }

    public bool IsRunning
    {
        get => _isRunning;
        private set
        {
            if (!SetProperty(ref _isRunning, value))
            {
                return;
            }

            _startCommand.RaiseCanExecuteChanged();
            _pauseCommand.RaiseCanExecuteChanged();
        }
    }

    public int UpdateIntervalMs
    {
        get => _updateIntervalMs;
        set
        {
            ObjectDisposedException.ThrowIf(_isDisposed, this);

            if (value is < MinimumIntervalMs or > MaximumIntervalMs)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(value),
                    $"Update interval must be between {MinimumIntervalMs} and {MaximumIntervalMs} ms.");
            }

            if (!SetProperty(ref _updateIntervalMs, value))
            {
                return;
            }

            _timer.Interval = TimeSpan.FromMilliseconds(value);
        }
    }

    public ICommand StartCommand => _startCommand;

    public ICommand PauseCommand => _pauseCommand;

    public void Dispose()
    {
        if (_isDisposed)
        {
            return;
        }

        _timer.Stop();
        _timer.Tick -= OnTimerTick;
        _isDisposed = true;
        IsRunning = false;
    }

    private static TickerViewModel CreateInstrument(
        string symbol,
        double initialPrice,
        double drift,
        double volatility)
    {
        return new TickerViewModel(
            new Instrument(symbol, initialPrice, drift, volatility));
    }

    private void Start()
    {
        ObjectDisposedException.ThrowIf(_isDisposed, this);

        if (IsRunning)
        {
            return;
        }

        _timer.Start();
        IsRunning = true;
    }

    private void Pause()
    {
        ObjectDisposedException.ThrowIf(_isDisposed, this);

        if (!IsRunning)
        {
            return;
        }

        _timer.Stop();
        IsRunning = false;
    }

    private void OnTimerTick(object? sender, EventArgs e)
    {
        // DispatcherTimer ticks on the UI thread, so bound properties and
        // observable histories can be updated without Dispatcher.Invoke.
        var deltaTime = UpdateIntervalMs / 1_000.0;

        foreach (var instrument in Instruments)
        {
            var nextPrice = _priceEngine.NextPrice(
                instrument.Price,
                instrument.Drift,
                instrument.Volatility,
                deltaTime);
            instrument.UpdatePrice(nextPrice);
        }
    }
}
