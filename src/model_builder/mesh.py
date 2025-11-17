"""
Meshing operations for composite impact simulations.

Handles:
- Mesh seeding and control
- Mesh generation
- Cohesive layer element set creation
"""

from typing import TYPE_CHECKING, Dict

from abaqus import *
from abaqusConstants import *

if TYPE_CHECKING:
    from abaqus.Part.Part import Part

from src.study_generator.model_input import ModelInput, SimulationConfig


def seed_and_mesh_laminate(
    lam_part: "Part", e_size: float, min_size_factor: float = 0.001
) -> None:
    """
    Seed and generate mesh for laminate part.

    Args:
        lam_part: Laminate part to mesh
        e_size: Element size in mm
        min_size_factor: Minimum size factor for mesh (default 0.001)
    """
    lam_part.setMeshControls(
        regions=lam_part.cells, technique=SWEEP, algorithm=MEDIAL_AXIS
    )
    lam_part.seedPart(size=e_size, deviationFactor=0.1, minSizeFactor=min_size_factor)
    lam_part.generateMesh()


def seed_and_mesh_impactor(imp_part: "Part", imp_radius: float) -> None:
    """
    Seed and generate mesh for impactor part.

    Args:
        imp_part: Impactor part to mesh
        imp_radius: Impactor radius for determining element size
    """
    # default value 5
    mesh_scale = 2
    imp_part.seedPart(size=imp_radius / mesh_scale)
    imp_part.setMeshControls(regions=imp_part.faces, technique=SWEEP)
    imp_part.generateMesh()


def seed_and_mesh_model(
    lam_parts: Dict[float, "Part"],
    lam_course_part: "Part",
    imp_part: "Part",
    sim_cfg: "SimulationConfig",
    cfg: "ModelInput",
) -> None:
    """
    Seed and mesh the laminate parts (refined and coarse).

    Args:
        lam_parts: Dictionary of refined laminate parts keyed by angle
        lam_course_part: Coarse laminate part
        sim_cfg: Simulation configuration object
        cfg: Model configuration object
    """
    min_size_factor = max(
        0.001, float(sim_cfg.mesh_refined) / float(sim_cfg.mesh_coarse)
    )

    for part in lam_parts.values():
        seed_and_mesh_laminate(part, sim_cfg.mesh_refined, min_size_factor)

    seed_and_mesh_laminate(lam_course_part, sim_cfg.mesh_coarse, min_size_factor)
    seed_and_mesh_impactor(imp_part, float(cfg.imp_radius))
