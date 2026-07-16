using CsharpApp.ViewModels;

namespace CsharpApp.Tests.ViewModels;

public sealed class MainViewModelTests
{
    [Fact]
    public async Task TimerPauseStartAndIntervalBehaveAsSpecified()
    {
        await StaTestRunner.RunAsync(async () =>
        {
            using var viewModel = new MainViewModel();

            Assert.Equal(5, viewModel.Instruments.Count);
            Assert.Equal("ALPHA", viewModel.SelectedInstrument?.Symbol);
            Assert.True(viewModel.IsRunning);
            Assert.False(viewModel.StartCommand.CanExecute(null));
            Assert.True(viewModel.PauseCommand.CanExecute(null));
            Assert.All(viewModel.Instruments, item => Assert.Single(item.History));

            Assert.Throws<ArgumentOutOfRangeException>(
                () => viewModel.UpdateIntervalMs = MainViewModel.MinimumIntervalMs - 1);
            Assert.Throws<ArgumentOutOfRangeException>(
                () => viewModel.UpdateIntervalMs = MainViewModel.MaximumIntervalMs + 1);

            viewModel.UpdateIntervalMs = MainViewModel.MaximumIntervalMs;
            Assert.Equal(MainViewModel.MaximumIntervalMs, viewModel.UpdateIntervalMs);

            viewModel.UpdateIntervalMs = MainViewModel.MinimumIntervalMs;
            Assert.Equal(MainViewModel.MinimumIntervalMs, viewModel.UpdateIntervalMs);
            var initialCounts = viewModel.Instruments.Select(item => item.History.Count).ToArray();

            await Task.Delay(450);

            for (var index = 0; index < viewModel.Instruments.Count; index++)
            {
                Assert.True(viewModel.Instruments[index].History.Count > initialCounts[index]);
            }

            viewModel.PauseCommand.Execute(null);
            Assert.False(viewModel.IsRunning);
            Assert.True(viewModel.StartCommand.CanExecute(null));
            Assert.False(viewModel.PauseCommand.CanExecute(null));

            var pausedCounts = viewModel.Instruments.Select(item => item.History.Count).ToArray();
            var pausedPrices = viewModel.Instruments.Select(item => item.Price).ToArray();

            await Task.Delay(300);

            Assert.Equal(
                pausedCounts,
                viewModel.Instruments.Select(item => item.History.Count).ToArray());
            Assert.Equal(
                pausedPrices,
                viewModel.Instruments.Select(item => item.Price).ToArray());

            viewModel.StartCommand.Execute(null);
            Assert.True(viewModel.IsRunning);

            await Task.Delay(300);

            for (var index = 0; index < viewModel.Instruments.Count; index++)
            {
                Assert.True(viewModel.Instruments[index].History.Count > pausedCounts[index]);
            }
        });
    }

}
