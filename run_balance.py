
import argparse
import time

from tactical_game.ai import selfplay


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=200)
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default="results")
    parser.add_argument("--tune", action="store_true", help="tune weights instead")
    args = parser.parse_args()

    started = time.time()
    if args.tune:
        weights, log = selfplay.tune_weights(
            games=args.games, depth=args.depth, seed=args.seed,
            log_path=f"{args.out}/tuning_log.csv")
        print(log.to_string())
        print("final weights:", weights)
    else:
        def show(record):
            if (record.game + 1) % 10 == 0:
                print(f"  {record.game + 1} games, {time.time() - started:.0f} s", flush=True)

        records = selfplay.run_selfplay(args.games, args.depth, args.seed, on_game=show)
        paths = selfplay.save_selfplay(records, args.out)
        for key, value in selfplay.summarize_selfplay(records).items():
            print(f"{key:30s} {value}")
        print("files:", paths["games"], paths["summary"])
    print(f"done in {time.time() - started:.0f} s")


if __name__ == "__main__":
    main()
