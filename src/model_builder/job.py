"""
Job creation and submission for composite impact simulations.

Handles:
- Job creation
- Job submission and monitoring
- Model report printing
"""

import sys
import subprocess
from typing import TYPE_CHECKING, Dict
import os

from abaqus import *
from abaqusConstants import *
from src.utils.logger import log_func, log_section
from src.utils.job_monitor import monitor_job

if TYPE_CHECKING:
    from abaqus.Model.Model import Model
    from abaqus.Part.Part import Part
    from src.study_generator.model_input import ModelInput


def create_and_submit_job(
    mdb: "Mdb",
    job_name: str,
    TEMP_DIR: str,
    model_name: str = "Model-1",
    wait: bool = True,
) -> None:
    """
    Create and submit Abaqus job with optional progress monitoring.

    Args:
        mdb: Abaqus MDB object
        job_name: Name for the job
        model_name: Name of the model to use (default "Model-1")
        wait: Whether to wait for job completion (default True)
        monitor: Whether to monitor progress in real-time (default True)
        sta_path: Path to .sta file for monitoring (required if monitor=True)
        total_time: Total simulation time for progress calculation (required if monitor=True)
    """
    # Try numCpus=4 when using project computer resources
    # Add numCpus and numDomains parameters to cfg and pass them here
    job = mdb.Job(
        name=job_name,
        model=model_name,
        description="Laminate impact with cohesive interlayers (Explicit).",
        explicitPrecision=DOUBLE_PLUS_PACK,
        numCpus=1,
        numDomains=1,
    )

    job.submit(consistencyChecking=ON)

    if wait:
        # Monitor job status every 10 seconds using python's time module
        sta_path = os.path.join(TEMP_DIR, f"{job_name}.sta")

        if monitor_job(sta_path):
            print("\n Job completed successfully by min KE.")
            job.kill()
            # Do command abaqus terminate job=Job_name through subprocess
            # subprocess.call(["taskkill", "/F", "/IM", "explicit_dp.exe"])
            subprocess.call(f"abaqus terminate job={job_name}", cwd=TEMP_DIR, shell=True)


def print_model_report(
    cfg: "ModelInput",
    ply_part: "Part",
    imp_part: "Part",
    lam_course_part: "Part",
    e_size_global: float,
    e_size_refined: float,
    simulation_time: float,
) -> None:
    """
    Print comprehensive model report to console.

    Args:
        cfg: Model configuration object
        lam_part: Refined laminate part
        imp_part: Impactor part
        e_size_global, e_size_refined: Element sizes
        simulation_time: Step time
        job_name: Job name
        lam_course_part: Optional coarse laminate part
    """

    nof_plies = cfg.n_ply

    log_section("MODEL REPORT")
    log_func("\n[Geometry]")
    log_func(
        "  Laminate size (mm):   L=%.3f  W=%.3f  T=%.3f"
        % (cfg.width, cfg.length, cfg.plate_T)
    )
    log_func("  Layer thickness (mm):  Ply=%.3f  Coh=%.3f" % (cfg.ply_thk, cfg.coh_thk))
    log_func(
        "  Stack:                %d plies, %d cohesive layers" % (cfg.n_ply, cfg.n_coh)
    )
    log_func("  Ply angles (deg):     %s" % cfg.ply_angles)

    log_func("\n[Mesh]")
    log_func(
        "  Elements:             %d"
        % (
            len(ply_part.elements) * nof_plies
            + len(lam_course_part.elements)
            + len(imp_part.elements)
        )
    )
    log_func(
        "  Nodes:                %d"
        % (
            len(ply_part.nodes) * nof_plies
            + len(lam_course_part.nodes)
            + len(imp_part.nodes)
        )
    )

    log_func(
        "  Element sizes (mm):   Refined=%.3f  Coarse=%.3f"
        % (e_size_refined, e_size_global)
    )

    log_func("\n[Impact]")
    log_func("  Impactor radius (mm): %.3f" % cfg.imp_radius)
    log_func(
        "  Impactor mass:        %.6f ton  (%.1f kg)"
        % (cfg.imp_mass, cfg.imp_mass * 1000.0)
    )
    log_func("  Impactor speed (mm/s):%.1f" % cfg.imp_speed)
    log_func("  Impact energy (J):    %.2f" % cfg.imp_energy_J)

    log_func("\n[Engineering constants]")
    log_func(
        "  E1/E2/E3 (MPa):       %.1f / %.1f / %.1f"
        % (cfg.material.E1, cfg.material.E2, cfg.material.E3)
    )
    log_func(
        "  nu12/nu23/nu13:       %.2f / %.2f / %.2f"
        % (cfg.material.NU12, cfg.material.NU23, cfg.material.NU13)
    )
    log_func(
        "  G12/G23/G13 (MPa):    %.1f / %.1f / %.1f"
        % (cfg.material.G12, cfg.material.G23, cfg.material.G13)
    )

    log_func("\n[Step]")
    log_func("  Step time (s):        %.6f" % simulation_time)
    log_func("  Job name:             %s" % cfg.job_name())
    log_func("=" * 60)
