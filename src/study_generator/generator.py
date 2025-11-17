"""
Simple parametric study generator.

User specifies parameters as lists in study.json.
Generates all combinations automatically.
"""

import json
import itertools
import os
from typing import Dict, List, Any, Tuple

from src.study_generator.model_input import ModelInput, MaterialSetup, SimulationConfig
from src.utils.logger import log_func, log_section
from src.utils.utils import create_directory


def load_study(study_path: str) -> Dict[str, Any]:
    """Load study configuration from JSON file."""
    with open(study_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_simulation_config(study_path: str) -> SimulationConfig:
    """
    Load simulation configuration from study file.

    Args:
        study_path: Path to study.json file

    Returns:
        SimulationConfig: Simulation parameters
    """
    study = load_study(study_path)
    sim_dict = study.get("simulation", {})
    return SimulationConfig.from_dict(sim_dict)


def generate_configs(
    study_path: str, time_stamp: str
) -> Tuple[List[ModelInput], SimulationConfig]:
    """
    Generate all parameter combinations from study file.

    Args:
        study_path: Path to study.json file

    Returns:
        Tuple of (list of ModelInput configuration objects, SimulationConfig)
    """
    study = load_study(study_path)

    # Load simulation configuration
    sim_config = SimulationConfig.from_dict(study.get("simulation", {}))

    # Extract parameter names and their value lists
    param_names = []
    param_values = []

    for name, param_def in study["parameters"].items():
        param_names.append(name)
        param_values.append(param_def["values"])

    # Generate all combinations
    configs = []

    for i, combo in enumerate(itertools.product(*param_values), start=1):
        # Create base config dictionary
        params = dict(zip(param_names, combo))

        # Get material properties from library
        mat_name = params["material"]
        mat_props = study["materials"][mat_name]

        # Create MaterialSetup object
        material = MaterialSetup.from_dict(mat_props)

        # Convert imp_mass_kg to tons (Abaqus units)
        imp_mass_ton = params["imp_mass_kg"] / 1000.0

        # Create ModelInput object
        model_input = ModelInput(
            uid=str(i),
            study=study["study_name"],
            created_at=time_stamp,
            units=study["units"],
            width=float(params["width"]),
            length=float(params["length"]),
            ply_angles=params["ply_angles"],
            ply_thk=float(params["ply_thk"]),
            coh_thk=float(params["coh_thk"]),
            imp_radius=float(params["imp_radius"]),
            imp_mass=imp_mass_ton,
            imp_speed=float(params["imp_speed"]),
            material_name=mat_name,
            material=material,
        )

        configs.append(model_input)

    return configs, sim_config


def create_case_json(
    case_num: int, time_stamp: str, param_set: dict, study_config: dict, output_dir: str
) -> Tuple[str, str]:
    """
    Create a JSON file for a single test case.

    Args:
        case_num: Case number (1, 2, 3, ...)
        param_set: Dictionary with parameter values for this case
        study_config: Full study configuration
        output_dir: Directory where case JSON will be saved
    """
    # Build complete case configuration
    case_config = {
        "case_id": case_num,
        "study_name": study_config["study_name"],
        "units": study_config["units"],
        "created_at": time_stamp,
        # Include all parameters for this case
        "parameters": param_set,
        # Include material definition
        "material_name": param_set.get("material", "MatA"),
        "material_properties": study_config["materials"][
            param_set.get("material", "MatA")
        ],
        # Include simulation settings
        "simulation": study_config["simulation"],
    }

    # Write to case file
    case_filename = "case{}.json".format(case_num)
    output_dir = os.path.join(output_dir, case_config["created_at"])
    case_path = os.path.join(output_dir, case_filename)

    create_directory(output_dir)

    with open(case_path, "w") as f:
        json.dump(case_config, f, indent=2)

    print("Created: {}".format(case_filename))

    job_name = f"{study_config['study_name']}_{case_num}"
    return case_path, job_name


def generate_parameter_combinations(parameters: dict) -> list[dict]:
    """
    Generate all combinations of parameter values.

    Args:
        parameters: Dictionary of parameter names and their values

    Returns:
        List of dictionaries, each representing one unique parameter set
    """
    # Extract parameter names and their value lists
    param_names = []
    param_values = []

    for param_name, param_data in parameters.items():
        param_names.append(param_name)
        param_values.append(param_data["values"])

    # Generate all combinations using itertools.product
    combinations = []
    for combo in itertools.product(*param_values):
        param_set = {}
        for name, value in zip(param_names, combo):
            param_set[name] = value
        combinations.append(param_set)

    return combinations


def split_study_into_cases(
    study_path: str, output_dir: str, time_stamp: str
) -> list[str]:
    """
    Split study.json into individual case files.

    Args:
        study_path: Path to study.json
        output_dir: Directory where case files will be created
    """
    # Load study configuration
    print("Loading study configuration from: {}".format(study_path))
    study_config = load_study(study_path)

    # Generate all parameter combinations
    print("Generating parameter combinations...")
    combinations = generate_parameter_combinations(study_config["parameters"])
    print("Found {} unique test cases".format(len(combinations)))

    # Create output directory if it doesn't exist
    create_directory(output_dir)

    # Create a JSON file for each case
    print("\nCreating case files...")
    case_files = []
    job_names = []
    for i, param_set in enumerate(combinations, start=1):
        case_path, job_name = create_case_json(
            i, time_stamp, param_set, study_config, output_dir
        )
        case_files.append(case_path)
        job_names.append(job_name)

    print("\n" + "=" * 50)
    print("SUCCESS: Created {} case files in {}".format(len(case_files), output_dir))
    print("=" * 50)

    return case_files, job_names


def from_case_to_model_input(case_path: str) -> ModelInput:
    """
    Convert a case JSON file to a ModelInput object.

    Args:
        case_path: Path to the case JSON file

    Returns:
        ModelInput object
    """
    with open(case_path, "r") as f:
        case_data = json.load(f)

    # Extract material properties
    mat_name = case_data["material_name"]
    mat_props = case_data["material_properties"]
    material = MaterialSetup.from_dict(mat_props)

    # Convert imp_mass_kg to tons (Abaqus units)
    imp_mass_ton = case_data["parameters"]["imp_mass_kg"]

    model_input = ModelInput(
        uid=str(case_data["case_id"]),
        study=case_data["study_name"],
        created_at=case_data["created_at"],
        units=case_data["units"],
        width=float(case_data["parameters"]["width"]),
        length=float(case_data["parameters"]["length"]),
        ply_angles=case_data["parameters"]["ply_angles"],
        ply_thk=float(case_data["parameters"]["ply_thk"]),
        coh_thk=float(case_data["parameters"]["coh_thk"]),
        imp_radius=float(case_data["parameters"]["imp_radius"]),
        imp_mass=imp_mass_ton,
        imp_speed=float(case_data["parameters"]["imp_speed"]),
        material_name=mat_name,
        material=material,
    )

    return model_input


def from_case_to_simulation_config(case_path: str) -> SimulationConfig:
    """
    Extract SimulationConfig from a case JSON file.

    Args:
        case_path: Path to the case JSON file

    Returns:
        SimulationConfig object
    """
    with open(case_path, "r") as f:
        case_data = json.load(f)

    sim_dict = case_data.get("simulation", {})
    return SimulationConfig.from_dict(sim_dict)


def from_case_to_configs(case_path: str) -> Tuple[ModelInput, SimulationConfig]:
    """
    Convert a case JSON file to ModelInput and SimulationConfig objects.

    Args:
        case_path: Path to the case JSON file

    Returns:
        Tuple of ModelInput and SimulationConfig objects
    """
    model_input = from_case_to_model_input(case_path)
    simulation_config = from_case_to_simulation_config(case_path)
    return model_input, simulation_config


def print_study_summary(study_path: str, time_stamp: str) -> None:
    configs = generate_configs(study_path, time_stamp)[0]

    log_section("PARAMETRIC STUDY SUMMARY")
    log_func(f"Total configurations: {len(configs)}")

    if configs:
        first = configs[0]
        log_func(f"\nStudy: {first.study}")
        log_func(f"Units: {first.units}")

        variations = {
            "ply_angles": len(set(str(c.ply_angles) for c in configs)),
            "ply_thk": len(set(c.ply_thk for c in configs)),
            "material": len(set(c.material_name for c in configs)),
            "imp_speed": len(set(c.imp_speed for c in configs)),
            "imp_mass": len(set(c.imp_mass for c in configs)),
            "imp_radius": len(set(c.imp_radius for c in configs)),
        }

        log_func("\nParameter variations:")
        for param, count in variations.items():
            log_func(f"  {param:20s}: {count} unique values")
