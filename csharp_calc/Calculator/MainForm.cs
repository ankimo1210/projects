using System;
using System.Drawing;
using System.Windows.Forms;

namespace Calculator;

public class MainForm : Form
{
    private readonly CalculatorEngine _engine = new();
    private readonly TextBox _display = new();

    public MainForm()
    {
        Text = "Calculator";
        ClientSize = new Size(300, 380);
        FormBorderStyle = FormBorderStyle.FixedSingle;
        MaximizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;

        _display.ReadOnly = true;
        _display.TabStop = false;
        _display.TextAlign = HorizontalAlignment.Right;
        _display.Text = "0";
        _display.Font = new Font("Segoe UI", 24F);
        _display.BorderStyle = BorderStyle.None;
        _display.Dock = DockStyle.Fill;

        var root = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 1,
            RowCount = 2,
        };
        root.RowStyles.Add(new RowStyle(SizeType.Absolute, 64F));
        root.RowStyles.Add(new RowStyle(SizeType.Percent, 100F));
        root.Controls.Add(_display, 0, 0);
        root.Controls.Add(BuildButtonGrid(), 0, 1);

        Controls.Add(root);
    }

    private TableLayoutPanel BuildButtonGrid()
    {
        var grid = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 4,
            RowCount = 5,
        };
        for (int c = 0; c < 4; c++)
            grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 25F));
        for (int r = 0; r < 5; r++)
            grid.RowStyles.Add(new RowStyle(SizeType.Percent, 20F));

        string[][] layout =
        {
            new[] { "7", "8", "9", "÷" },
            new[] { "4", "5", "6", "×" },
            new[] { "1", "2", "3", "−" },
            new[] { "0", ".", "=", "+" },
        };

        for (int r = 0; r < layout.Length; r++)
            for (int c = 0; c < layout[r].Length; c++)
                grid.Controls.Add(MakeButton(layout[r][c]), c, r);

        var clear = MakeButton("C");
        grid.Controls.Add(clear, 0, 4);
        grid.SetColumnSpan(clear, 4);

        return grid;
    }

    private Button MakeButton(string text)
    {
        var button = new Button
        {
            Text = text,
            Dock = DockStyle.Fill,
            Font = new Font("Segoe UI", 16F),
            Margin = new Padding(3),
            FlatStyle = FlatStyle.System,
        };
        button.Click += (_, _) => OnButtonClick(text);
        return button;
    }

    private void OnButtonClick(string text)
    {
        _display.Text = text switch
        {
            "C" => _engine.Clear(),
            "=" => _engine.Evaluate(),
            "." => _engine.InputDecimal(),
            "÷" => _engine.InputOperator('/'),
            "×" => _engine.InputOperator('*'),
            "−" => _engine.InputOperator('-'),
            "+" => _engine.InputOperator('+'),
            _ => _engine.InputDigit(text),
        };
    }
}
