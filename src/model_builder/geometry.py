"""
Geometry creation functions for composite impact simulations.

Handles creation of:
- Refined zone parts (impact region)
- Coarse zone parts (outer frame)
- Impactor geometry
- Layer stack calculation
"""

from typing import TYPE_CHECKING, List, Tuple

from abaqus import *
from abaqusConstants import *
import mesh
import regionToolset

if TYPE_CHECKING:
    from abaqus.Model.Model import Model
    from abaqus.Part.Part import Part

from src.study_generator.model_input import ModelInput


class StackLayer:
    """
    Helper class to track layer position and properties in the laminate stack.

    Attributes:
        type: Layer type ('ply' or 'coh')
        thk: Layer thickness in mm
        ang: Fiber angle in degrees (for plies) or reference angle (for cohesive)
        z_mid: Z-coordinate of layer mid-plane
        z_bot: Z-coordinate of layer bottom surface
        z_top: Z-coordinate of layer top surface
    """

    def __init__(
        self,
        typ: str,
        thk: float,
        ang: float,
        z_mid: float,
        z_bot: float,
        z_top: float,
    ) -> None:
        self.type = typ
        self.thk = thk
        self.ang = ang
        self.z_mid = z_mid
        self.z_bot = z_bot
        self.z_top = z_top


def calculate_layer_stack(
    ply_angles: List[int], ply_thk: float, coh_thk: float
) -> List[StackLayer]:
    """
    Calculate the layer stack with positions for all plies and cohesive layers.

    Args:
        ply_angles: List of ply angles in degrees (bottom to top)
        ply_thk: Ply thickness in mm
        coh_thk: Cohesive layer thickness in mm

    Returns:
        List of StackLayer objects with z-positions calculated
    """
    z_bot = 0.0
    stack_layers = []

    for i, ang in enumerate(ply_angles):
        stack_layers.append(
            StackLayer(
                "ply",
                ply_thk,
                float(ang),
                z_bot + 0.5 * ply_thk,
                z_bot,
                z_bot + ply_thk,
            )
        )
        z_bot += ply_thk
    return stack_layers


def make_refined_block(
    model: "Model",
    plate_W: float,
    plate_L: float,
    name: str,
    thickness: float,
    angle: float,
) -> "Part":
    """
    Create a rectangular solid part for the refined (impact) zone.

    Args:
        model: Abaqus Model object
        plate_W: Plate width in mm
        plate_L: Plate length in mm
        name: Name for the part
        thickness: Extrusion depth (layer thickness) in mm

    Returns:
        Part object with dimensions plate_W x plate_L x thickness
    """
    sk = model.ConstrainedSketch(
        name="sk_" + name, sheetSize=max(plate_W, plate_L) * 10.0
    )
    sk.rectangle((-plate_W / 2.0, -plate_L / 2.0), (plate_W / 2.0, plate_L / 2.0))
    part = model.Part(name=name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseSolidExtrude(sketch=sk, depth=thickness)
    del model.sketches["sk_" + name]
    return part


def make_outer_coarse_block(
    model: "Model",
    plate_W: float,
    plate_L: float,
    S: float,
    name: str,
    thickness: float,
) -> "Part":
    """
    Create a frame part for the coarse (outer) zone with rectangular cutout.

    The frame has outer dimensions S x plate_W x S x plate_L with a hole
    matching the refined block dimensions (plate_W x plate_L).

    Args:
        model: Abaqus Model object
        plate_W: Plate width in mm
        plate_L: Plate length in mm
        S: Scale factor for outer dimensions
        name: Name for the part
        thickness: Extrusion depth (layer thickness) in mm

    Returns:
        Part object representing the coarse outer frame
    """
    sk = model.ConstrainedSketch(
        name="sk_" + name, sheetSize=max(plate_W, plate_L) * 10.0
    )
    sk.rectangle(
        (-S * plate_W / 2.0, -S * plate_L / 2.0), (S * plate_W / 2.0, S * plate_L / 2.0)
    )
    sk.rectangle((-plate_W / 2.0, -plate_L / 2.0), (plate_W / 2.0, plate_L / 2.0))
    part = model.Part(name=name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseSolidExtrude(sketch=sk, depth=thickness)

    del model.sketches["sk_" + name]
    return part


def create_impactor(model: "Model", imp_radius: float) -> "Part":
    """
    Create a rigid hemispherical impactor part.

    Args:
        model: Abaqus Model object
        imp_radius: Impactor radius in mm

    Returns:
        Part object for the rigid impactor surface
    """
    sk = model.ConstrainedSketch(name="sk_imp", sheetSize=imp_radius * 2.0)
    sk.ConstructionLine(point1=(0.0, -100.0), point2=(0.0, 100.0))
    sk.ArcByCenterEnds(
        center=(0.0, imp_radius),
        point1=(imp_radius, imp_radius),
        point2=(0.0, 0.0),
        direction=CLOCKWISE,
    )
    imp_part = model.Part(
        name="Impactor", dimensionality=THREE_D, type=DISCRETE_RIGID_SURFACE
    )
    imp_part.BaseShellRevolve(sketch=sk, angle=360.0, flipRevolveDirection=OFF)
    del model.sketches["sk_imp"]
    return imp_part


def create_geometry(
    model: "Model",
    cfg: ModelInput,
    S: float,
) -> Tuple["Part", "Part", "Part", "Part", "Part"]:
    """
    Create all geometry parts for the model.

    Args:
        model: Abaqus Model object
        cfg: ModelInput configuration object

    Returns:
        Tuple of created Part objects
        (part_ply, part_ply_course, part_coh, part_coh_course, part_impactor)
    """

    # Create a refined block for each unique ply angle
    unique_angles = list(set(cfg.ply_angles))

    # Create a dictionary to hold the parts for each angle
    part_ply = {}

    for angle in unique_angles:
        part_name = f"Ply_Angle_{int(angle)}"
        part_ply[angle] = make_refined_block(
            model, cfg.width, cfg.length, part_name, cfg.ply_thk, angle
        )
    part_ply_course = make_outer_coarse_block(
        model, cfg.width, cfg.length, S, "Ply_Course", cfg.ply_thk
    )

    part_impactor = create_impactor(model, cfg.imp_radius)

    return (part_ply, part_ply_course, part_impactor)
