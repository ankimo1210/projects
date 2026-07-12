from optimal_execution.cli import main

raise SystemExit(main(["train-rl", *__import__("sys").argv[1:]]))
