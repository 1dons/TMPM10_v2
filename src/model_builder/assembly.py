"""
Assembly operations for composite impact simulations.

Handles:
- Layer stacking and merging
- Instance creation and positioning
- Tie constraints between refined and coarse regions
- Datum coordinate systems
"""

from typing import TYPE_CHECKING, List, Tuple
from xml.parsers.expat import model

from abaqus import *
from interaction import *
from abaqusConstants import *


if TYPE_CHECKING:
    from abaqus.Model.Model import Model
    from abaqus.Part.Part import Part
    from abaqus.Assembly.Assembly import Assembly
    from abaqus.Assembly.PartInstance import PartInstance

from src.model_builder.geometry import StackLayer
from src.study_generator.model_input import ModelInput
from src.model_builder.boundary_conditions import create_rigid_body_and_mass


def merge_laminate_stack(
    asm: "Assembly",
    stack_layers: List[StackLayer],
    part_ply: "Part",
    prefix: str = "I",
) -> None:
    """
    Create and merge instances of plies and cohesive layers into a laminate.

    Args:
        asm: Abaqus Assembly object
        stack_layers: List of StackLayer objects defining the stack
        part_ply: Template part for plies
        part_coh: Template part for cohesive layers
        prefix: Prefix for instance names (default "I" for refined, "IC" for coarse)

    Creates a merged part named "Laminate" or "Laminate_Course"
    """
    to_merge = []
    for i, layer in enumerate(stack_layers):
        base = part_ply
        iname = "%s_%s_%02d" % (prefix, "Ply", i)
        inst = asm.Instance(name=iname, part=base, dependent=ON)
        asm.translate(instanceList=(iname,), vector=(0.0, 0.0, layer.z_bot))
        to_merge.append(inst)

    merge_name = "Laminate_Course"
    asm.InstanceFromBooleanMerge(
        name=merge_name,
        instances=tuple(to_merge),
        keepIntersections=ON,
        originalInstances=DELETE,
        domain=GEOMETRY,
    )


def add_datum_coordinate_system(part: "Part") -> None:
    """
    Add a datum coordinate system to a part at the origin.

    Args:
        part: Part object to add datum to
    """
    part.DatumCsysByThreePoints(
        name="SYS",
        coordSysType=CARTESIAN,
        origin=(0.0, 0.0, 0.0),
        line1=(1.0, 0.0, 0.0),
        line2=(0.0, 1.0, 0.0),
    )


def create_tie_faces(
    lam_instances: List["PartInstance"],
    lam_course_inst: "PartInstance",
    stack_layers: List[StackLayer],
    plate_W: float,
    plate_L: float,
) -> Tuple[List, List]:
    """
    Identify faces at the interface between refined and coarse regions for tie constraint.

    Args:
        lam_inst: Refined laminate instance
        lam_course_inst: Coarse laminate instance
        stack_layers: List of StackLayer objects
        plate_W: Plate width in mm
        plate_L: Plate length in mm

    Returns:
        Tuple of (tie_faces1, tie_faces2) for refined and coarse regions
    """
    tie_faces1 = []
    tie_faces2 = []

    for i, layer in enumerate(stack_layers):
        z_mid = layer.z_mid
        connecting_pos = [
            (plate_W / 2, 0.0, z_mid),
            (0.0, plate_L / 2, z_mid),
            (-plate_W / 2, 0.0, z_mid),
            (0.0, -plate_L / 2, z_mid),
        ]
        for pos in connecting_pos:
            tie_faces1.append(lam_instances[i].faces.findAt((pos,)))
            tie_faces2.append(lam_course_inst.faces.findAt((pos,)))

    return tie_faces1, tie_faces2


def create_tie_constraint(
    model: "Model", asm: "Assembly", tie_faces1: List, tie_faces2: List
) -> None:
    """
    Create tie constraint between refined and coarse laminate regions.

    Args:
        model: Abaqus Model object
        asm: Abaqus Assembly object
        tie_faces1: List of faces from refined region
        tie_faces2: List of faces from coarse region
    """
    surf1 = asm.Surface(name="Tie_Surf_Lam", side1Faces=tie_faces1)
    surf2 = asm.Surface(name="Tie_Surf_LamCourse", side1Faces=tie_faces2)
    model.Tie(
        name="Tie_Lam_Fine_Course",
        main=surf2,
        secondary=surf1,
        positionToleranceMethod=COMPUTED,
        adjust=ON,
        tieRotations=ON,
        thickness=ON,
        constraintEnforcement=SURFACE_TO_SURFACE,
    )


def position_impactor(
    asm: "Assembly", imp_part: "Part", plate_T: float, imp_radius: float
) -> int:
    """
    Create impactor instance, rotate, and position above the plate.

    Args:
        asm: Abaqus Assembly object
        imp_part: Impactor part
        plate_T: Total plate thickness in mm
        imp_radius: Impactor radius in mm

    Returns:
        Tuple of (ref_point_id, impactor_height)
    """
    asm.Instance(name="Impactor", part=imp_part, dependent=ON)
    asm.rotate(
        instanceList=("Impactor",),
        axisPoint=(0.0, 0.0, 0.0),
        axisDirection=(1.0, 0.0, 0.0),
        angle=90.0,
    )
    impactor_height = plate_T + 1e-6
    asm.translate(instanceList=("Impactor",), vector=(0.0, 0.0, impactor_height))

    # Create reference point for impactor
    ref_pt = asm.ReferencePoint(point=(0.0, 0.0, impactor_height + imp_radius))

    return ref_pt.id


def create_laminate_stack(
    asm: "Assembly",
    stack_layers: List[StackLayer],
    unique_plies: dict["float", "Part"],
) -> List["PartInstance"]:
    """
    Create the laminate stack by stacking instances

    Args:
        asm: Abaqus Assembly object
        stack_layers: List of StackLayer objects defining the stack
        cfg: ModelInput configuration object
    """
    # Create the laminate assembly by instancing and translating each layer part
    instances = []
    for i, layer in enumerate(stack_layers):
        # Check angle and get correct part
        if layer.ang == 0.0:
            base = unique_plies[0.0]
            iname = "IC_Ply_%02d" % (i)
        elif layer.ang == 45.0:
            base = unique_plies[45.0]
            iname = "IC_Ply_%02d" % (i)
        elif layer.ang == -45.0:
            base = unique_plies[-45.0]
            iname = "IC_Ply_%02d" % (i)
        elif layer.ang == 90.0:
            base = unique_plies[90.0]
            iname = "IC_Ply_%02d" % (i)
        instances.append(asm.Instance(name=iname, part=base, dependent=ON))
        asm.translate(instanceList=(iname,), vector=(0.0, 0.0, layer.z_bot))

    return instances


def assemble_model(
    model: "Model", asm: "Assembly", parts, stack_layers, cfg: ModelInput
) -> Tuple:
    """
    Assemble the model by merging laminate stacks and preparing instances.

    Args:
        model: Abaqus Model object
        asm: Abaqus Assembly object
        parts: Tuple of created Part objects
        stack_layers: List of StackLayer objects defining the stack
        cfg: ModelInput configuration object

    Returns:
        Tuple of merged parts and instantiated parts
    """
    part_ply, part_ply_course, part_impactor = parts

    asm.DatumCsysByDefault(CARTESIAN)

    merge_laminate_stack(asm, stack_layers, part_ply_course, prefix="IC")
    lam_course_part = model.parts["Laminate_Course"]
    add_datum_coordinate_system(lam_course_part)
    lam_course_inst = asm.instances["Laminate_Course-1"]

    lam_instances = create_laminate_stack(asm, stack_layers, part_ply)

    create_tie_constraint(
        model,
        asm,
        *create_tie_faces(
            lam_instances, lam_course_inst, stack_layers, cfg.width, cfg.length
        ),
    )

    # ---------------------- Position impactor ----------------------
    rp_id = position_impactor(asm, part_impactor, cfg.plate_T, cfg.imp_radius)
    create_rigid_body_and_mass(model, asm, rp_id, cfg)

    imp_inst = asm.instances["Impactor"]
    return (
        (part_ply, lam_course_part, part_impactor),
        (lam_instances, lam_course_inst, imp_inst),
    )
