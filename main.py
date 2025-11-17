import os
import sys
import inspect


# Set up project root and paths
_THIS = inspect.getfile(inspect.currentframe())
PROJ_ROOT = os.path.abspath(os.path.dirname(_THIS))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from src.study_generator.generator import from_case_to_configs, split_study_into_cases
from src.model_builder.builder import build_model_and_job
from src.utils.utils import create_directory
from src.utils.logger import init_logger, close_logger

# Import Abaqus modules
from abaqus import *
from abaqusConstants import *
import mesh
import regionToolset
from typing import List


# Define main directories
INPUTS_DIR = os.path.join(PROJ_ROOT, "inputs")
OUTPUTS_DIR = os.path.join(PROJ_ROOT, "outputs")
TEMP_DIR = os.path.join(PROJ_ROOT, "temp")


if __name__ == "__main__":
    for dir_path in [OUTPUTS_DIR, TEMP_DIR]:
        create_directory(dir_path)

    study_path = os.path.join(INPUTS_DIR, "study.json")
    case_path = os.path.join(TEMP_DIR, "cases")
    case_files, job_names = split_study_into_cases(study_path, case_path, "20250505")

    case_file = case_files[0]
    cfg, sim_cfg = from_case_to_configs(case_file)

    init_logger(OUTPUTS_DIR)

    os.chdir(TEMP_DIR)

    mdb.close()
    model = mdb.Model(name="Model-1")
    build_model_and_job(sim_config=sim_cfg, cfg=cfg, model=model, TEMP_DIR=TEMP_DIR)
    close_logger()
