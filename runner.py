#!/usr/bin/env python3

import argparse
import glob
import importlib
import os
import pickle
import matplotlib
import numpy as np

DEFAULT_MPL_BACKEND = matplotlib.get_backend()
matplotlib.use("Cairo")  # backend without X server requirements
import matplotlib.pyplot as plt

from libbench import (
    VendorBenchmark,
    VendorLink,
    VendorJobManager,
    print_hl,
    print_stderr,
)


"""
    Definitions of constants
"""

# find runnable test modules and vendors
BENCHMARKS = [
    os.path.basename(folder)
    for folder in glob.glob("./benchmarks/*")
    if os.path.isdir(folder) and not os.path.basename(folder) == "__pycache__"
]
VENDORS = [
    os.path.basename(folder)
    for folder in glob.glob("./libbench/*")
    if os.path.isdir(folder) and not os.path.basename(folder) == "__pycache__"
]

MODE_CLASS_NAMES = {
    "cloud": "Cloud",
    "measure_local": "MeasureLocal",
    "statevector": "Statevector",
}
MODES = list(MODE_CLASS_NAMES.keys())


"""
    Import Functionality for benchmarks, links and jobmanagers
"""


def import_benchmark(name, vendor, mode, device):
    benchmark_module = importlib.import_module(f"benchmarks.{name}.{vendor}")
    return getattr(benchmark_module, "SimulatedBenchmark" if mode == "Statevector" else "Benchmark")


def import_link(vendor, mode):
    vendor_module = importlib.import_module(f"libbench.{vendor}")
    return getattr(vendor_module, mode + "Link")


def import_jobmanager(vendor):
    vendor_module = importlib.import_module(f"libbench.{vendor}")
    return getattr(vendor_module, "JobManager")


def import_argparser(name, toadd, **argparse_options):
    benchmark_module = importlib.import_module(f"benchmarks.{name}")
    argparser = getattr(benchmark_module, "argparser")
    return argparser(toadd, **argparse_options)


def obtain_jobmanager(job_id, run_folder, recreate_device):
    VendorJobManager.RUN_FOLDER = run_folder
    slug = VendorJobManager.load(job_id)
    jobmanager = slug["jobmanager"]

    # restore stuff saved along job manager to recreate device where we run the benchmark on
    VENDOR, DEVICE, MODE = (
        slug["additional_stored_info"]["vendor"],
        slug["additional_stored_info"]["device"],
        slug["additional_stored_info"]["mode"],
    )

    # recreate device if demanded to do so
    device = None
    if recreate_device:
        link = import_link(VENDOR, MODE)()
        device = link.get_device(DEVICE)

        jobmanager.thaw(device)

    return jobmanager, device, slug


"""
    INFO
"""


def info_vendor(args):
    VENDOR = args.vendor

    for mode, MODE in MODE_CLASS_NAMES.items():
        link = import_link(VENDOR, MODE)()
        devices = link.get_devices()
        print(f"Available {mode} devices:")
        if len(devices) == 0:
            print_hl("No devices available.", color="red")
        else:
            for name in devices:
                print(name)
        print()


def info_benchmark(parser_benchmarks, args):
    BENCHMARK = args.benchmark
    assert BENCHMARK in BENCHMARKS

    argparser = parser_benchmarks[BENCHMARK]
    argparser.print_help()


"""
    BENCHMARK and RESUME
"""


def _show_figure(figpath):
    import webbrowser

    webbrowser.open_new(str(figpath))


def _run_update(
    jobmanager: VendorJobManager,
    device: object,
    additional_stored_info: dict,
    show_directly: bool = False,
):
    if not jobmanager.update(
        device,
        additional_stored_info=additional_stored_info,
        figure_callback=_show_figure if show_directly else lambda *x: None,
    ):
        print(f"benchmark not done. Resume by calling ./runner.py resume {jobmanager.ID}")


def resume_benchmark(args):
    RUN_FOLDER = args.run_folder
    JOB_ID = args.job_id
    jobmanager, device, slug = obtain_jobmanager(JOB_ID, RUN_FOLDER, recreate_device=True)

    # run update
    _run_update(jobmanager, device, slug["additional_stored_info"])


def new_benchmark(args):
    VENDOR = args.vendor
    DEVICE = args.device
    BENCHMARK = args.benchmark
    MODE = MODE_CLASS_NAMES[args.mode]
    RUN_FOLDER = args.run_folder  # we do not validate this since the folder is created on-the-fly

    assert VENDOR in VENDORS, "vendor does not exist"
    assert BENCHMARK is None or BENCHMARK in BENCHMARKS, "benchmark does not exist"

    # pick vendor
    Link = import_link(VENDOR, MODE)
    link = Link()

    # check device exists
    assert DEVICE in link.get_devices(), "device does not exist"

    device = link.get_device(DEVICE)
    Benchmark = import_benchmark(BENCHMARK, VENDOR, MODE, DEVICE)
    JobManager = import_jobmanager(VENDOR)
    JobManager.RUN_FOLDER = RUN_FOLDER
    jobmanager = JobManager(Benchmark(topology=link.get_device_topology(DEVICE), **vars(args)))

    # run update
    _run_update(
        jobmanager,
        device,
        additional_stored_info={
            "vendor": VENDOR,
            "mode": MODE,
            "device": DEVICE,
            "benchmark": BENCHMARK,
        },
        show_directly=args.show_directly,
    )


"""
    REFRESH
"""


def _get_job_ids(run_folder):
    # sort directories increasingly with respect to ctime
    dirs = list(filter(os.path.isdir, glob.glob(f"{run_folder}/*")))
    dirs.sort(key=lambda x: os.path.getctime(x))
    return [
        os.path.basename(folder)
        for folder in dirs
        if not os.path.basename(folder) in {"__pycache__", "obsolete"}
    ]


def refresh(args):
    RUN_FOLDER = args.run_folder
    ALL = args.all
    job_ids = args.job_ids if not ALL else _get_job_ids(RUN_FOLDER)

    for JOB_ID in job_ids:
        print(f"refreshing {JOB_ID}...", end=" ")
        jobmanager, *_ = obtain_jobmanager(JOB_ID, RUN_FOLDER, recreate_device=False)

        if jobmanager.done:
            jobmanager.finalize()
            print("done.")
        else:
            print("not done yet.")


"""
    SCORE
"""


def score(args):
    RUN_FOLDER = args.run_folder

    # benchmark to score
    BENCHMARK_ID = args.benchmark
    jobmanager_bench, _, slug_bench = obtain_jobmanager(
        BENCHMARK_ID, RUN_FOLDER, recreate_device=False
    )
    if not jobmanager_bench.done:
        print_stderr("benchmark not done yet")
        return
    BENCHMARK = slug_bench["additional_stored_info"]["benchmark"]

    # optional, a reference benchmark
    REFERENCE_ID = args.reference
    if REFERENCE_ID:
        jobmanager_ref, _, slug_ref = obtain_jobmanager(
            REFERENCE_ID, RUN_FOLDER, recreate_device=False
        )
        if not jobmanager_ref.done:
            print_stderr("reference not done yet")
            return
        if slug_ref["additional_stored_info"]["benchmark"] != BENCHMARK:
            print_stderr("benchmark and reference are not the same test")
            return

    jobmanager_bench.score(
        jobmanager_bench.collate_results(),
        jobmanager_ref.collate_results() if REFERENCE_ID else None,
    )


"""
    STATUS
"""
import random


def status(args):
    RUN_FOLDER = args.run_folder
    VendorJobManager.print_legend()

    job_ids = _get_job_ids(RUN_FOLDER)
    for job_id in random.sample(job_ids, len(job_ids)):
        print(f"Obtaining status for {job_id}.")
        jobmanager, _, slug = obtain_jobmanager(job_id, RUN_FOLDER, recreate_device=False)
        jobmanager.print_status(tail=slug["additional_stored_info"])
        jobmanager.save_additional_info_files(slug["additional_stored_info"])


"""
    TEX
"""


def make_tex(args):
    results = {}
    RUN_FOLDER = args.run_folder
    for x in os.listdir(RUN_FOLDER):
        print("Going into folder:", x)
        job_ids = _get_job_ids(RUN_FOLDER + "/" + x)

        for job_id in random.sample(job_ids, len(job_ids)):
            print(f"Obtaining status for {job_id}.")
            jobmanager, _, slug = obtain_jobmanager(
                job_id, RUN_FOLDER + "/" + x, recreate_device=False
            )
            benchmark = "-".join(str(jobmanager.benchmark).split("--")[0].split("-")[1:])
            print("Benchmark:", benchmark)
            if benchmark not in results:
                results[benchmark] = {}
            vendor = slug["additional_stored_info"]["vendor"]
            device = slug["additional_stored_info"]["device"]
            if device.startswith("ibmq_"):
                device = device[5:]
            if device.startswith("Aspen"):
                device = "-".join(device.split("-")[:2]).lower()
            if device.startswith("16_"):
                device = device[3:]
            print(f"  vendor: {vendor}.")
            print(f"  device: {device}.")
            if (vendor, device) not in results[benchmark]:
                results[benchmark][(vendor, device)] = {}
            if benchmark in ["Schroedinger-Microscope", "Mandelbrot"]:
                print(f"  #post-selections: {jobmanager.benchmark.num_post_selections}.")
                print(f"  #pixels: {jobmanager.benchmark.num_pixels}.")
                print(f"  #shots: {jobmanager.benchmark.num_shots}.")
                results[benchmark][(vendor, device)][
                    (
                        jobmanager.benchmark.num_post_selections,
                        jobmanager.benchmark.num_pixels,
                        jobmanager.benchmark.num_shots,
                    )
                ] = (job_id, jobmanager.benchmark.score(jobmanager.collate_results(), None))
            elif benchmark == "Line-Drawing":
                print(f"  #points: {len(jobmanager.benchmark.points)}")
                print(f"  #shots: {jobmanager.benchmark.num_shots}")
                print(f"  #repetitions: {jobmanager.benchmark.num_repetitions}")
                results[benchmark][(vendor, device)][
                    (
                        len(jobmanager.benchmark.points),
                        jobmanager.benchmark.num_shots,
                        jobmanager.benchmark.num_repetitions,
                    )
                ] = (job_id, jobmanager.benchmark.score(jobmanager.collate_results(), None))
            else:
                print("Score not processed.")

    for benchmark, res in sorted(
        results.items(),
        key=lambda x: [
            "Schroedinger-Microscope",
            "Mandelbrot",
            "Line-Drawing",
            "Platonic-Fractals",
        ].index(x[0]) if x in [
            "Schroedinger-Microscope",
            "Mandelbrot",
            "Line-Drawing",
            "Platonic-Fractals",
        ] else float('inf'),
    ):
        print()
        print(f"TeX for {benchmark}:")
        if benchmark in ["Schroedinger-Microscope", "Mandelbrot"]:
            for i, ((vendor, device), r) in enumerate(
                sorted(res.items(), key=lambda x: ((3, 32, 8192) in x[1], x))
            ):
                if i % 4 == 0:
                    print()
                    print("\\noindent")
                job_id = list(r.values())[0][0]
                year, month = job_id.split("--")[1].split("-")[:2]
                date = "{} {}".format(
                    [
                        "Jan",
                        "Feb",
                        "Mar",
                        "Apr",
                        "May",
                        "Jun",
                        "Jul",
                        "Aug",
                        "Sep",
                        "Oct",
                        "Nov",
                        "Dec",
                    ][int(month) - 1],
                    year,
                )
                if (1, 32, 4096) in r and (2, 32, 4096) in r:
                    avg_score = 0.25 * (
                        r[(1, 32, 4096)][1][0][0]
                        + r[(1, 32, 4096)][1][1][0]
                        + r[(2, 32, 4096)][1][0][0]
                        + r[(2, 32, 4096)][1][1][0]
                    )
                    sigma_avg_score = 0.25 * np.linalg.norm(
                        [
                            r[(1, 32, 4096)][1][0][1],
                            r[(1, 32, 4096)][1][1][1],
                            r[(2, 32, 4096)][1][0][1],
                            r[(2, 32, 4096)][1][1][1],
                        ]
                    )
                else:
                    avg_score, sigma_avg_score = "?", "?"
                if (3, 32, 8192) in r:
                    print(
                        "\\{}LargeResultsCard{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}".format(
                            "SM" if benchmark == "Schroedinger-Microscope" else "Mandelbrot",
                            vendor,
                            device,
                            "{:.4f} {{\\color{{gray}}{{\pm {:.4f}}}}}".format(
                                *r[(1, 32, 4096)][1][0]
                            )
                            if (1, 32, 4096) in r
                            else "?",
                            "{:.4f} {{\\color{{gray}}{{\pm {:.4f}}}}}".format(
                                *r[(1, 32, 4096)][1][1]
                            )
                            if (1, 32, 4096) in r
                            else "?",
                            "{:.4f} {{\\color{{gray}}{{\pm {:.4f}}}}}".format(
                                *r[(2, 32, 4096)][1][0]
                            )
                            if (2, 32, 4096) in r
                            else "?",
                            "{:.4f} {{\\color{{gray}}{{\pm {:.4f}}}}}".format(
                                *r[(2, 32, 4096)][1][1]
                            )
                            if (2, 32, 4096) in r
                            else "?",
                            "{:.4f} {{\\color{{gray}}{{\pm {:.4f}}}}}".format(
                                *r[(3, 32, 8192)][1][0]
                            )
                            if (3, 32, 8192) in r
                            else "?",
                            "{:.4f} {{\\color{{gray}}{{\pm {:.4f}}}}}".format(
                                *r[(3, 32, 8192)][1][1]
                            )
                            if (3, 32, 8192) in r
                            else "?",
                            date,
                            "{:.4f} {{\\color{{gray}}{{\pm {:.4f}}}}}".format(
                                avg_score, sigma_avg_score
                            )
                            if avg_score != "?" and sigma_avg_score != "?"
                            else "?",
                        )
                    )
                else:
                    print(
                        "\\{}SmallResultsCard{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}{{{}}}".format(
                            "SM" if benchmark == "Schroedinger-Microscope" else "Mandelbrot",
                            vendor,
                            device,
                            "{:.4f} {{\\color{{gray}}{{\pm {:.4f}}}}}".format(
                                *r[(1, 32, 4096)][1][0]
                            )
                            if (1, 32, 4096) in r
                            else "?",
                            "{:.4f} {{\\color{{gray}}{{\pm {:.4f}}}}}".format(
                                *r[(1, 32, 4096)][1][1]
                            )
                            if (1, 32, 4096) in r
                            else "?",
                            "{:.4f} {{\\color{{gray}}{{\pm {:.4f}}}}}".format(
                                *r[(2, 32, 4096)][1][0]
                            )
                            if (2, 32, 4096) in r
                            else "?",
                            "{:.4f} {{\\color{{gray}}{{\pm {:.4f}}}}}".format(
                                *r[(2, 32, 4096)][1][1]
                            )
                            if (2, 32, 4096) in r
                            else "?",
                            date,
                            "{:.4f} {{\\color{{gray}}{{\pm {:.4f}}}}}".format(
                                avg_score, sigma_avg_score
                            )
                            if avg_score != "?" and sigma_avg_score != "?"
                            else "?",
                        )
                    )
        if benchmark == "Line-Drawing":
            for i, ((vendor, device), r) in enumerate(sorted(res.items())):
                if i % 4 == 0:
                    print()
                    print("\\noindent")
                job_id = list(r.values())[0][0]
                year, month = job_id.split("--")[2].split("-")[:2]
                date = "{} {}".format(
                    [
                        "Jan",
                        "Feb",
                        "Mar",
                        "Apr",
                        "May",
                        "Jun",
                        "Jul",
                        "Aug",
                        "Sep",
                        "Oct",
                        "Nov",
                        "Dec",
                    ][int(month) - 1],
                    year,
                )
                avg_score = (
                    (r[(4, 4096, 25)][1][0] + r[(8, 4096, 25)][1][0]) / 2
                    if (4, 4096, 25) in r and (8, 4096, 25) in r
                    else (r[(4, 4096, 128)][1][0] + r[(8, 4096, 32)][1][0]) / 2
                    if (4, 4096, 128) in r and (8, 4096, 32) in r
                    else (r[(4, 8096, 25)][1][0] + r[(8, 8096, 25)][1][0]) / 2
                    if (4, 8096, 25) in r and (8, 8096, 25) in r
                    else (r[(4, 8192, 25)][1][0] + r[(8, 8192, 25)][1][0]) / 2
                    if (4, 8192, 25) in r and (8, 8192, 25) in r
                    else "?"
                )
                sigma_avg = (
                    np.linalg.norm([r[(4, 4096, 25)][1][1], r[(8, 4096, 25)][1][1]]) / 2
                    if (4, 4096, 25) in r and (8, 4096, 25) in r
                    else np.linalg.norm([r[(4, 4096, 128)][1][1], r[(8, 4096, 32)][1][1]]) / 2
                    if (4, 4096, 128) in r and (8, 4096, 32) in r
                    else np.linalg.norm([r[(4, 8096, 25)][1][1], r[(8, 8096, 25)][1][1]]) / 2
                    if (4, 8096, 25) in r and (8, 8096, 25) in r
                    else np.linalg.norm([r[(4, 8192, 25)][1][1], r[(8, 8192, 25)][1][1]]) / 2
                    if (4, 8192, 25) in r and (8, 8192, 25) in r
                    else "?"
                )
                print(
                    "\\lineResultsCard{{{}}}{{{}}}{{{}}}{{{}}}[{}][{}][{}]".format(
                        vendor,
                        device,
                        "{:.2f}+{:.2f}".format(avg_score, sigma_avg)
                        if avg_score != "?" and sigma_avg != "?"
                        else "?",
                        date,
                        "{:.2f}+{:.2f}".format(*r[(4, 4096, 25)][1])
                        if (4, 4096, 25) in r
                        else "{:.2f}+{:.2f}".format(*r[(4, 4096, 128)][1])
                        if (4, 4096, 128) in r
                        else "{:.2f}+{:.2f}".format(*r[(4, 8096, 25)][1])
                        if (4, 8096, 25) in r
                        else "{:.2f}+{:.2f}".format(*r[(4, 8192, 25)][1])
                        if (4, 8192, 25) in r
                        else "?",
                        "{:.2f}+{:.2f}".format(*r[(8, 4096, 25)][1])
                        if (8, 4096, 25) in r
                        else "{:.2f}+{:.2f}".format(*r[(8, 4096, 32)][1])
                        if (8, 4096, 32) in r
                        else "{:.2f}+{:.2f}".format(*r[(8, 8096, 25)][1])
                        if (8, 8096, 25) in r
                        else "{:.2f}+{:.2f}".format(*r[(8, 8192, 25)][1])
                        if (8, 8192, 25) in r
                        else "?",
                        "{:.2f}+{:.2f}".format(*r[(16, 4096, 25)][1])
                        if (16, 4096, 25) in r
                        else "{:.2f}+{:.2f}".format(*r[(16, 8096, 25)][1])
                        if (16, 8096, 25) in r
                        else "{:.2f}+{:.2f}".format(*r[(16, 8192, 25)][1])
                        if (16, 8192, 25) in r
                        else "?",
                    )
                )


if __name__ == "__main__":
    print_hl("qυanтυм вencнмarĸιng ѕυιтe\n", color="cyan")

    # arguments
    argparse_options = {"formatter_class": argparse.ArgumentDefaultsHelpFormatter}
    parser = argparse.ArgumentParser(description="Quantum Benchmark", **argparse_options)
    subparsers = parser.add_subparsers(metavar="ACTION", help="Action you want to take")

    # new benchmark
    parser_A = subparsers.add_parser("benchmark", help="Run new benchmark", **argparse_options)
    parser_A.set_defaults(func=new_benchmark)
    parser_A.add_argument(
        "vendor",
        metavar="VENDOR",
        type=str,
        help=f"vendor to use; one of {', '.join(VENDORS)}",
    )
    parser_A.add_argument(
        "mode", metavar="MODE", type=str, help=f"mode to run; one of {', '.join(MODES)}"
    )
    parser_A.add_argument(
        "device",
        metavar="DEVICE",
        type=str,
        help="device to use with chosen vendor; run ./runner.py info vendor VENDOR to get a list.",
    )
    parser_A.add_argument(
        "--show_directly",
        action="store_true",
        help="show the visualization if the benchmark completes directly.",
    )
    parser_A.add_argument(
        "--run_folder",
        default=VendorJobManager.RUN_FOLDER,
        help=f"folder to store benchmark jobs in; created if it does not exist",
    )
    subparsers_A = parser_A.add_subparsers(metavar="BENCHMARK", help="benchmark to run")

    parser_benchmarks = {}
    for benchmark in BENCHMARKS:
        parser_benchmark = import_argparser(benchmark, subparsers_A, **argparse_options)
        parser_benchmark.set_defaults(benchmark=benchmark)
        parser_benchmarks[benchmark] = parser_benchmark

    # info
    parser_I = subparsers.add_parser(
        "info", help="Information for vendors or benchmarks", **argparse_options
    )
    parser_I.set_defaults(func=lambda args: parser_I.print_help())
    subparsers_I = parser_I.add_subparsers(metavar="TYPE", help="Type of information requested")

    # vendor info
    parser_IV = subparsers_I.add_parser(
        "vendor", help="Information about devices", **argparse_options
    )
    parser_IV.set_defaults(func=info_vendor)
    parser_IV.add_argument(
        "vendor",
        metavar="VENDOR",
        type=str,
        default=False,
        help=f"vendor to use; one of {', '.join(VENDORS)}",
    )

    # benchmark info
    parser_IB = subparsers_I.add_parser(
        "benchmark", help="Information about benchmarks", **argparse_options
    )
    parser_IB.set_defaults(func=lambda args: info_benchmark(parser_benchmarks, args))
    parser_IB.add_argument(
        "benchmark",
        metavar="BENCHMARK",
        type=str,
        help=f"benchmark to use; one of {', '.join(BENCHMARKS)}",
    )

    # resume benchmark
    parser_R = subparsers.add_parser("resume", help="Resume old benchmark", **argparse_options)
    parser_R.set_defaults(func=resume_benchmark)
    parser_R.add_argument(
        "job_id",
        metavar="JOB_ID",
        type=str,
        help=f"old job id; subfolder name in {VendorJobManager.RUN_FOLDER}",
    )
    parser_R.add_argument(
        "--run_folder",
        default=VendorJobManager.RUN_FOLDER,
        help=f"folder to store benchmark jobs in; created if it does not exist",
    )

    # update collation and visualization steps of jobmanager
    parser_V = subparsers.add_parser(
        "refresh",
        help="Update already completed benchmarks from individual job runs.",
        **argparse_options,
    )
    parser_V.set_defaults(func=refresh)
    parser_V.add_argument("--all", action="store_true", help="refresh all completed benchmarks")
    parser_V.add_argument("job_ids", nargs="*")
    parser_V.add_argument(
        "--run_folder",
        default=VendorJobManager.RUN_FOLDER,
        help=f"run folder within which to refresh runs",
    )

    # print benchmark scores
    parser_SC = subparsers.add_parser("score", help="Score benchmark", **argparse_options)
    parser_SC.set_defaults(func=score)
    parser_SC.add_argument(
        "benchmark",
        metavar="BENCHMARK",
        type=str,
        help=f"benchmark id; subfolder name in {VendorJobManager.RUN_FOLDER}",
    )
    parser_SC.add_argument(
        "--reference",
        metavar="REFERENCE",
        type=str,
        help=f"reference benchmark id; subfolder name in {VendorJobManager.RUN_FOLDER}",
    )
    parser_SC.add_argument(
        "--run_folder",
        default=VendorJobManager.RUN_FOLDER,
        help=f"folder to store benchmark jobs in; created if it does not exist",
    )

    # benchmark status
    parser_S = subparsers.add_parser(
        "status", help="Display the status of all benchmarks.", **argparse_options
    )
    parser_S.set_defaults(func=status)
    parser_S.add_argument(
        "--run_folder",
        default=VendorJobManager.RUN_FOLDER,
        help=f"folder to store benchmark jobs in; created if it does not exist",
    )

    parser_T = subparsers.add_parser(
        "tex", help="Generate the TeX to be put in the paper.", **argparse_options
    )
    parser_T.set_defaults(func=make_tex)
    parser_T.add_argument(
        "--run_folder",
        default=VendorJobManager.RUN_FOLDER,
        help=f"folder where the benchmark jobs are stored.",
    )

    args = parser.parse_args()

    # correctly parsed? otherwise show help
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
