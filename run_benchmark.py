"""Run the Q31 benchmark end to end 
    python run_benchmark.py  # depths 1-4, 5 repetitions
    python run_benchmark.py --depths 1 2 3 --repetitions 5
"""

import argparse
import time
from tactical_game.ai import benchmark
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--depths", type=int, nargs="+", default=list(benchmark.DEFAULT_DEPTHS))
    parser.add_argument("--repetitions", type=int, default=benchmark.DEFAULT_REPETITIONS)
    parser.add_argument("--out", default="results")
    parser.add_argument("--late-game", action="store_true", help="add the sixth scenario")
    args = parser.parse_args()

    started = time.time()
    rows = benchmark.run_benchmark(
        benchmark.build_scenarios(include_late_game=args.late_game),
        depths=args.depths, repetitions=args.repetitions)
    paths = benchmark.save_results(rows, args.out)
    benchmark.plot_benchmark(paths["raw"], f"{args.out}/benchmark.png")

    branching = benchmark.measure_branching(benchmark.random_playout_states(20, seed=1))
    print(benchmark.summarize(rows).to_string())
    print("branching:", branching)
    print(f"done in {time.time() - started:.0f} s; files in {args.out}/")


if __name__ == "__main__":
    main()
