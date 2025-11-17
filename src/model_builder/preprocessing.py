"""
Preprocessing operations for composite impact simulations.

Handles:
- Section assignments to cells
- Material orientations
- Element type assignments
"""

from typing import TYPE_CHECKING, Dict, List

from abaqus import *
from abaqusConstants import *
import regionToolset

if TYPE_CHECKING:
    from abaqus.Part.Part import Part
    from abaqus.Mesh.ElemType import ElemType

from src.model_builder.geometry import StackLayer
from src.study_generator.model_input import ModelInput


def assign_sections_and_orientations(
    lam_parts: Dict[float, "Part"],
    lam_course_part: "Part",
    impactor_part: "Part",
    stack_layers: List[StackLayer],
    cfg: "ModelInput",
    elem_ply: "ElemType",
    elem_impactor: "ElemType",
) -> None:
    """
    Assign sections, material orientations, and element types to laminate layers.

    Args:
        lam_part: Refined laminate part
        lam_course_part: Coarse laminate part (can be None)
        stack_layers: List of StackLayer objects
        cfg: Model configuration object
        elem_ply: Element type for plies
        elem_coh: Element type for cohesive layers

    """

    # Assign element type for impactor
    impactor_part.setElementType(
        regions=(impactor_part.faces,), elemTypes=(elem_impactor,)
    )

    for angle, part in lam_parts.items():
        part.setElementType(regions=(part.cells,), elemTypes=(elem_ply,))
        reg = regionToolset.Region(cells=part.cells)
        part.SectionAssignment(region=reg, sectionName="LamSec")
        part.MaterialOrientation(
            region=reg,
            orientationType=SYSTEM,
            axis=AXIS_3,
            localCsys=None,
            additionalRotationType=ROTATION_ANGLE,
            additionalRotationField="",
            angle=angle,
            stackDirection=STACK_ORIENTATION,
        )

    for layer in stack_layers:
        z_mid = layer.z_mid

        # Find cells in coarse region
        cells_course = lam_course_part.cells.findAt(((cfg.width, 0, z_mid),))
        reg_course = regionToolset.Region(cells=cells_course)

        lam_course_part.SectionAssignment(region=reg_course, sectionName="LamSec")
        lam_course_part.MaterialOrientation(
            region=reg_course,
            orientationType=SYSTEM,
            axis=AXIS_3,
            localCsys=None,
            additionalRotationType=ROTATION_ANGLE,
            additionalRotationField="",
            angle=layer.ang,
            stackDirection=STACK_ORIENTATION,
        )
        lam_course_part.setElementType(regions=(cells_course,), elemTypes=(elem_ply,))
