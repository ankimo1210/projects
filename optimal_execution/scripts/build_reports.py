from optimal_execution.cli import main

raise SystemExit(main(["report", "--locale", "all", *__import__("sys").argv[1:]]))
