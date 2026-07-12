from optimal_execution.cli import main

raise SystemExit(main(["all", *__import__("sys").argv[1:]]))
