"""Run every experiment and redraw the plots.

    python -m experiments.run_all          (about 10-15 minutes)
"""

from experiments import benchmark, tournament, plot_results

if __name__ == "__main__":
    benchmark.main()
    tournament.main()
    plot_results.main()
