"""
Contact definitions for composite impact simulations.

Handles:
- General contact definitions
- Contact properties (friction, normal behavior)
- Surface-to-surface interactions
"""

from typing import TYPE_CHECKING, List

from abaqus import *
from abaqusConstants import *
import regionToolset

if TYPE_CHECKING:
    from abaqus.Model.Model import Model
    from abaqus.Assembly.Assembly import Assembly
    from abaqus.Assembly.PartInstance import PartInstance

from src.study_generator.model_input import ModelInput
from src.model_builder.geometry import StackLayer


def create_general_contact(model: "Model", cfg: "ModelInput") -> None:
    """
    Create general contact with frictionless default behavior.

    Args:
        model: Abaqus Model object
    """
    model.ContactProperty("GeneralContactProp")
    model.interactionProperties["GeneralContactProp"].TangentialBehavior(
        formulation=FRICTIONLESS
    )
    model.interactionProperties["GeneralContactProp"].NormalBehavior(
        pressureOverclosure=HARD,
        allowSeparation=ON,
        constraintEnforcementMethod=DEFAULT,
    )

    model.ContactExp(name="General_Contact", createStepName="Initial")
    model.interactions["General_Contact"].includedPairs.setValuesInStep(
        stepName="Initial", useAllstar=ON
    )

    model.interactions["General_Contact"].contactPropertyAssignments.appendInStep(
        stepName="Initial", assignments=((GLOBAL, SELF, "GeneralContactProp"),)
    )


def create_cohesive_layer_contact(
    model: "Model",
    asm: "Assembly",
    lam_instances: List["PartInstance"],
    cfg: "ModelInput",
    stack_layers: List[StackLayer],
) -> None:
    """
    Create cohesive contact between plies

    Args:
        model: Abaqus Model object
        asm: Assembly object
        coh_inst: Cohesive layer part instance
    """

    mat = cfg.material

    model.ContactProperty("Cohesive_contact")
    model.interactionProperties["Cohesive_contact"].CohesiveBehavior(
        defaultPenalties=OFF,
        table=(
            (mat.En / 0.1, mat.G1 / 0.1, mat.G2 / 0.1),
        ),  # Penalty stiffnesses Kn Kt Kb (Divided by thickness)
    )
    model.interactionProperties["Cohesive_contact"].Damage(
        criterion=QUAD_TRACTION,
        initTable=((mat.N, mat.S1, mat.S2),),  # These are the peak strengths
        useEvolution=ON,
        evolutionType=ENERGY,
        useMixedMode=ON,
        mixedModeType=BK,
        exponent=1.45,  # BK exponent
        evolTable=((mat.GIc, mat.GIIc, mat.GIIIc),),  # This is the GIc value
        viscosityCoef=1.0,
    )

    model.interactionProperties["Cohesive_contact"].NormalBehavior(
        pressureOverclosure=HARD,
        allowSeparation=ON,
        constraintEnforcementMethod=DEFAULT,
    )

    for i, layer in enumerate(stack_layers):
        z_top = layer.z_top

        # Between every ply except the top one
        if i != len(stack_layers) - 1:
            top_face_i = lam_instances[i].faces.findAt(((0.0, 0.0, z_top),))
            bottom_face_ip1 = lam_instances[i + 1].faces.findAt(((0.0, 0.0, z_top),))

            top_i = asm.Surface(name="Cohesive_Top_%d" % i, side1Faces=top_face_i)
            bottom_ip1 = asm.Surface(
                name="Cohesive_Bottom_%d" % (i + 1), side1Faces=bottom_face_ip1
            )

        model.interactions["General_Contact"].contactPropertyAssignments.appendInStep(
            stepName="Initial",
            assignments=((top_i, bottom_ip1, "Cohesive_contact"),),
        )


def create_impactor_contact(
    model: "Model",
    asm: "Assembly",
    imp_inst: "PartInstance",
    lam_inst: "PartInstance",
    plate_T: float,
    friction_coeff: float = 0.3,
) -> None:
    """
    Create contact between impactor and laminate with friction.

    Args:
        model: Abaqus Model object
        asm: Assembly object
        imp_faces: Impactor face sequence
        lam_inst: Laminate instance
        plate_T: Total plate thickness in mm
        friction_coeff: Friction coefficient (default 0.3)
    """
    model.ContactProperty("Impactor_Laminate_CP")
    model.interactionProperties["Impactor_Laminate_CP"].TangentialBehavior(
        formulation=PENALTY,
        directionality=ISOTROPIC,
        table=((friction_coeff,),),
        maximumElasticSlip=FRACTION,
        fraction=0.005,
    )
    model.interactionProperties["Impactor_Laminate_CP"].NormalBehavior(
        pressureOverclosure=HARD,
        allowSeparation=ON,
        constraintEnforcementMethod=DEFAULT,
    )

    # Create surfaces
    imp_surf = asm.Surface(name="Surf_Impactor", side1Faces=imp_inst.faces)
    lam_top_faces = lam_inst.faces.findAt(((0.0, 0.0, plate_T),))
    lam_surface = asm.Surface(name="Surf_LamTop", side1Faces=lam_top_faces)

    # Assign contact property
    model.interactions["General_Contact"].contactPropertyAssignments.appendInStep(
        stepName="Initial",
        assignments=((lam_surface, imp_surf, "Impactor_Laminate_CP"),),
    )


def create_contacts(
    model: "Model",
    asm: "Assembly",
    lam_instances: List["PartInstance"],
    imp_inst: "PartInstance",
    cfg: "ModelInput",
    stack_layers: List[StackLayer],
) -> None:
    """
    Create contacts for the model.

    Args:
        model: Abaqus Model object
        asm: Assembly object
        lam_inst: Laminate instance
        imp_inst: Impactor instance
        cfg: ModelInput configuration object
    """
    create_general_contact(model, cfg)

    create_cohesive_layer_contact(model, asm, lam_instances, cfg, stack_layers)

    create_impactor_contact(
        model,
        asm,
        imp_inst,
        lam_instances[-1],
        cfg.plate_T,
        friction_coeff=0.3,
    )
