from optimal_execution.cli import main

raise SystemExit(main(["evaluate", *__import__("sys").argv[1:]]))
