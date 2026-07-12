from optimal_execution.cli import main

raise SystemExit(main(["lob", *__import__("sys").argv[1:]]))
