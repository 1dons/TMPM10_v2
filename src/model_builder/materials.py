"""
Material and section definitions for composite impact simulations.

Handles creation of:
- Lamina (orthotropic) materials
- Cohesive materials with traction-separation
- Element type definitions
- Section assignments
"""

from typing import TYPE_CHECKING, Tuple

from abaqus import *
from abaqusConstants import *
import mesh
from src.study_generator.model_input import ModelInput

if TYPE_CHECKING:
    from abaqus.Model.Model import Model


def create_lamina_material(
    model: "Model",
    E1: float,
    E2: float,
    E3: float,
    NU12: float,
    NU13: float,
    NU23: float,
    G12: float,
    G13: float,
    G23: float,
    rho_lam: float,
) -> None:
    """
    Create orthotropic lamina material and section.

    Args:
        model: Abaqus Model object
        E1, E2, E3: Elastic moduli in MPa
        NU12, NU13, NU23: Poisson's ratios
        G12, G13, G23: Shear moduli in MPa
        rho_lam: Density in ton/mm³
    """
    mat_lam = model.Material("LamMat")
    mat_lam.Density(table=((rho_lam,),))
    mat_lam.Elastic(
        type=ENGINEERING_CONSTANTS,
        table=((E1, E2, E3, NU12, NU13, NU23, G12, G13, G23),),
    )
    model.HomogeneousSolidSection(name="LamSec", material="LamMat")


def create_element_types() -> Tuple:
    """
    Create element type definitions for explicit analysis.

    Returns:
        Tuple of (elem_ply, elem_coh, elem_impactor):
            - elem_ply: C3D8I for composite plies
            - elem_coh: COH3D8 for cohesive layers
            - elem_impactor: R3D4 for rigid impactor surface
    """
    elem_ply = mesh.ElemType(
        elemCode=C3D8I,
        elemLibrary=EXPLICIT,
        secondOrderAccuracy=OFF,
        distortionControl=DEFAULT,
    )
    elem_impactor = mesh.ElemType(elemCode=R3D4)

    return elem_ply, elem_impactor


def create_materials(model: "Model", cfg: ModelInput) -> None:
    """
    Create materials and sections in the Abaqus model based on cfg.

    Args:
        cfg: ModelInput object with material properties
    """
    create_lamina_material(
        model=model,
        E1=cfg.material.E1,
        E2=cfg.material.E2,
        E3=cfg.material.E3,
        NU12=cfg.material.NU12,
        NU13=cfg.material.NU13,
        NU23=cfg.material.NU23,
        G12=cfg.material.G12,
        G13=cfg.material.G13,
        G23=cfg.material.G23,
        rho_lam=cfg.material.rho_lam,
    )
