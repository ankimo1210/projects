from rough_volatility.cli import main

raise SystemExit(main(["report", "--locale", "all", *__import__("sys").argv[1:]]))
