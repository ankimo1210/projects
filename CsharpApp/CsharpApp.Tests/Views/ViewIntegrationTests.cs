using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;
using System.Windows.Threading;
using CsharpApp.Models;
using CsharpApp.ViewModels;
using CsharpApp.Views;

namespace CsharpApp.Tests.Views;

public sealed class ViewIntegrationTests
{
    [Fact]
    public async Task MainWindowLoadsExpectedBindingsAndControlSettings()
    {
        await StaTestRunner.RunAsync(async () =>
        {
            var window = new MainWindow();
            var viewModel = Assert.IsType<MainViewModel>(window.DataContext);

            try
            {
                window.Show();
                window.UpdateLayout();

                var dataGrid = Assert.IsType<DataGrid>(window.FindName("TickerGrid"));
                var slider = Assert.IsType<Slider>(window.FindName("IntervalSlider"));
                var chart = Assert.IsType<SparklineControl>(window.FindName("PriceChart"));

                Assert.Same(viewModel.Instruments, dataGrid.ItemsSource);
                Assert.Same(viewModel.SelectedInstrument, dataGrid.SelectedItem);
                Assert.Equal(MainViewModel.MinimumIntervalMs, slider.Minimum);
                Assert.Equal(MainViewModel.MaximumIntervalMs, slider.Maximum);
                Assert.Equal(50, slider.TickFrequency);
                Assert.True(slider.IsSnapToTickEnabled);
                Assert.Equal(MainViewModel.DefaultIntervalMs, slider.Value);
                Assert.Same(viewModel.SelectedInstrument?.History, chart.Values);

                var nextInstrument = viewModel.Instruments[1];
                dataGrid.SelectedItem = nextInstrument;
                await Dispatcher.Yield(DispatcherPriority.DataBind);

                Assert.Same(nextInstrument, viewModel.SelectedInstrument);
                Assert.Same(nextInstrument.History, chart.Values);
            }
            finally
            {
                window.Close();
            }
        });
    }

    [Fact]
    public async Task SparklineHandlesSparseFlatLiveAndResizedSeries()
    {
        await StaTestRunner.RunAsync(async () =>
        {
            var chart = new SparklineControl();
            chart.Measure(new Size(300, 120));
            chart.Arrange(new Rect(0, 0, 300, 120));

            var line = Assert.IsType<Polyline>(chart.Children[0]);
            var point = Assert.IsType<Ellipse>(chart.Children[1]);

            chart.Values = Array.Empty<double>();
            Assert.Empty(line.Points);
            Assert.Equal(Visibility.Collapsed, point.Visibility);

            var history = new PriceHistoryBuffer(4);
            history.Add(100);
            chart.Values = history;
            chart.RaiseEvent(new RoutedEventArgs(FrameworkElement.LoadedEvent));

            Assert.Empty(line.Points);
            Assert.Equal(Visibility.Visible, point.Visibility);

            history.Add(100);

            Assert.Equal(2, line.Points.Count);
            Assert.All(line.Points, value => Assert.Equal(60.0, value.Y, 6));
            Assert.Equal(Visibility.Collapsed, point.Visibility);

            history.Add(110);

            Assert.Equal(3, line.Points.Count);
            Assert.Equal(8.0, line.Points[0].X, 6);
            Assert.Equal(292.0, line.Points[^1].X, 6);
            Assert.Equal(8.0, line.Points[^1].Y, 6);

            chart.Width = 500;
            chart.Height = 220;
            chart.InvalidateMeasure();
            chart.Measure(new Size(500, 220));
            chart.Arrange(new Rect(0, 0, 500, 220));
            await Dispatcher.Yield(DispatcherPriority.Render);

            Assert.Equal(500.0, chart.ActualWidth, 6);
            Assert.Equal(220.0, chart.ActualHeight, 6);
            Assert.Equal(492.0, line.Points[^1].X, 6);
            Assert.Equal(8.0, line.Points[^1].Y, 6);

            chart.RaiseEvent(new RoutedEventArgs(FrameworkElement.UnloadedEvent));
        });
    }

    [Fact]
    public async Task PriceFlashRestartsAndIgnoresUnchangedPrice()
    {
        await StaTestRunner.RunAsync(() =>
        {
            var ticker = new TickerViewModel(new Instrument("TEST", 100, 0, 0));
            var row = new DataGridRow { DataContext = ticker };
            PriceFlashBehavior.SetIsEnabled(row, true);
            row.RaiseEvent(new RoutedEventArgs(FrameworkElement.LoadedEvent));

            ticker.UpdatePrice(101);
            var firstBrush = Assert.IsType<SolidColorBrush>(row.Background);

            ticker.UpdatePrice(102);
            var secondBrush = Assert.IsType<SolidColorBrush>(row.Background);
            Assert.NotSame(firstBrush, secondBrush);

            row.ClearValue(Control.BackgroundProperty);
            ticker.UpdatePrice(102);
            Assert.Null(row.Background);

            row.RaiseEvent(new RoutedEventArgs(FrameworkElement.UnloadedEvent));
            PriceFlashBehavior.SetIsEnabled(row, false);
            return Task.CompletedTask;
        });
    }
}
