from rough_volatility.cli import main

# argparse last-wins: a caller-supplied --locale overrides the default "all".
raise SystemExit(main(["report", "--locale", "all", *__import__("sys").argv[1:]]))
