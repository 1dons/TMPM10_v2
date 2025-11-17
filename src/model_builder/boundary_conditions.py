"""
Boundary conditions and initial conditions for composite impact simulations.

Handles:
- Displacement boundary conditions
- Simply-supported and clamped edges
- Initial velocity conditions
- Reference point constraints
"""

from typing import TYPE_CHECKING, List

from abaqus import *
from abaqusConstants import *
import regionToolset

if TYPE_CHECKING:
    from abaqus.Model.Model import Model
    from abaqus.Assembly.Assembly import Assembly
    from abaqus.Assembly.PartInstance import PartInstance

from src.model_builder.geometry import StackLayer
from src.study_generator.model_input import ModelInput


def apply_plate_boundary_conditions(
    model: "Model",
    lam_course_inst: "PartInstance",
    stack_layers: List[StackLayer],
    plate_W: float,
    plate_L: float,
    S: float,
) -> None:
    """
    Apply clamped short edges and simply-supported long edges to the plate.

    Args:
        model: Abaqus Model object
        lam_inst: Refined laminate instance
        lam_course_inst: Coarse laminate instance (can be None)
        stack_layers: List of StackLayer objects
        plate_W: Plate width in mm
        plate_L: Plate length in mm
        S: Scale factor for coarse region
        use_coarse: Whether to apply BCs to coarse region
    """

    # Clamp short edges (±X faces at all z)
    clamped_faces = lam_course_inst.faces.findAt(
        ((S * plate_W / 2.0, 0.0, stack_layers[0].z_mid),)
    )
    clamped_faces += lam_course_inst.faces.findAt(
        ((-S * plate_W / 2.0, 0.0, stack_layers[0].z_mid),)
    )
    for layer in stack_layers[1:]:
        clamped_faces += lam_course_inst.faces.findAt(
            ((S * plate_W / 2.0, 0.0, layer.z_mid),)
        )
        clamped_faces += lam_course_inst.faces.findAt(
            ((-S * plate_W / 2.0, 0.0, layer.z_mid),)
        )

    # Simply supported long edges (±Y edges at z=bottom)
    long_edges = lam_course_inst.edges.findAt(
        ((0.0, S * plate_L / 2.0, stack_layers[0].z_bot),)
    )
    long_edges += lam_course_inst.edges.findAt(
        ((0.0, -S * plate_L / 2.0, stack_layers[0].z_bot),)
    )

    # Apply boundary conditions
    model.DisplacementBC(
        name="BC_ShortEdges_Clamped",
        createStepName="Initial",
        region=regionToolset.Region(faces=clamped_faces),
        u1=SET,
        u2=SET,
        u3=SET,
    )
    model.DisplacementBC(
        name="BC_LongEdges_SimplySupported",
        createStepName="Initial",
        region=regionToolset.Region(edges=long_edges),
        u1=UNSET,
        u2=UNSET,
        u3=SET,
    )


def create_rigid_body_and_mass(
    model: "Model", asm: "Assembly", rp_id: int, cfg: ModelInput
) -> None:
    """
    Create rigid body definition and assign point mass to impactor.

    Args:
        model: Abaqus Model object
        asm: Assembly object
        rp_id: Reference point ID
        cfg: ModelInput object containing impactor properties
    """
    imp_faces = asm.instances["Impactor"].faces
    set_imp = asm.Set(faces=imp_faces, name="Set-Impactor")
    rp_region = regionToolset.Region(referencePoints=(asm.referencePoints[rp_id],))

    model.RigidBody(name="Impactor_RB", refPointRegion=rp_region, bodyRegion=set_imp)
    asm.engineeringFeatures.PointMassInertia(
        name="Impactor_Mass",
        region=rp_region,
        mass=cfg.imp_mass,
        i11=0.0,
        i22=0.0,
        i33=0.0,
        alpha=0.0,
        composite=0.0,
    )

    # Apply constraints and initial velocity
    # Apply impactor constraints
    model.DisplacementBC(
        name="BC_RP_NoSpin",
        createStepName="Initial",
        region=rp_region,
        u1=SET,
        u2=SET,
        u3=UNSET,
        ur1=SET,
        ur2=SET,
        ur3=SET,
    )

    # Set initial velocity
    model.Velocity(
        name="IC_Impactor_V0",
        region=rp_region,
        velocity1=0.0,
        velocity2=0.0,
        velocity3=-cfg.imp_speed,
        omega=0.0,
        axisBegin=(0.0, 0.0, 0.0),
        axisEnd=(0.0, 0.0, 1.0),
    )
