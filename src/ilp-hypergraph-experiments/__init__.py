from .ilps.graph import run_model as graph_model
from .ilps.hypergraph import run_hyper_model, configure_model
from .benchmark import benchmark, mean, var
from tqdm import tqdm
import gurobipy as gp
import time
import argparse


def main_benchmark():
    """Entry point for the application script"""
    n = 10
    res_graph = benchmark(graph_model, n=n)

    times_hypergraph_gen: list[int] = []
    times_hypergraph_solve: list[int] = []
    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)
        env.start()
        print("Benchmark 'configure_model' and solving it seperatly:")
        for _ in tqdm(range(n)):
            with gp.Model(env=env) as m:
                tic = time.perf_counter()
                configure_model(m, verbose=False)
                toc = time.perf_counter()
                times_hypergraph_gen.append(toc - tic)

                tic = time.perf_counter()
                m.optimize()
                toc = time.perf_counter()
                times_hypergraph_solve.append(toc - tic)

    times_hypergraph_total = list(
        x + y for x, y in zip(times_hypergraph_gen, times_hypergraph_solve)
    )

    print()
    res_hypergraph_gen = (
        "Benchmarked function 'configure_model'.\nMean: "
        + str(mean(times_hypergraph_gen))
        + ", Variance: "
        + str(var(times_hypergraph_gen))
        + ", Range: "
        + str(min(times_hypergraph_gen))
        + "-"
        + str(max(times_hypergraph_gen))
    )
    res_hypergraph_solve = (
        "Benchmarked solving model.\nMean: "
        + str(mean(times_hypergraph_solve))
        + ", Variance: "
        + str(var(times_hypergraph_solve))
        + ", Range: "
        + str(min(times_hypergraph_solve))
        + "-"
        + str(max(times_hypergraph_solve))
    )
    res_hypergraph_total = (
        "Benchmarked hypergraph combined.\nMean: "
        + str(mean(times_hypergraph_total))
        + ", Variance: "
        + str(var(times_hypergraph_total))
        + ", Range: "
        + str(min(times_hypergraph_total))
        + "-"
        + str(max(times_hypergraph_total))
    )
    print(res_graph)
    print(res_hypergraph_gen)
    print(res_hypergraph_solve)
    print(res_hypergraph_total)


def main_run():
    graph_model(verbose=True)
    print("\n#####################\nCompleted Graph Model\n#####################\n")
    run_hyper_model(verbose=True)


def main():
    parser = argparse.ArgumentParser(
        description="Experiment to hypergraphs.\nPer default both the graph and hypergraph model will be solved."
    )
    parser.add_argument(
        "--bench",
        dest="bench",
        action="store_const",
        const=True,
        default=False,
        help="Run the benchmark instead of solving the model.",
    )
    args = parser.parse_args()
    if args.bench:
        main_benchmark()
    else:
        main_run()


if __name__ == "__main__":
    main()
