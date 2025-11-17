from typing import TYPE_CHECKING

from abaqus import *
from abaqusConstants import *

from src.study_generator.model_input import ModelInput

# Import submodules
from src.model_builder.geometry import (
    calculate_layer_stack,
    create_geometry,
)
from src.model_builder.materials import (
    create_materials,
    create_element_types,
)
from src.model_builder.assembly import assemble_model

from src.model_builder.mesh import seed_and_mesh_model

from src.model_builder.preprocessing import assign_sections_and_orientations
from src.model_builder.boundary_conditions import (
    apply_plate_boundary_conditions,
)
from src.model_builder.contact import create_contacts
from src.model_builder.step_and_output import (
    create_explicit_step,
    configure_field_outputs,
)

from src.model_builder.job import create_and_submit_job, print_model_report


if TYPE_CHECKING:
    from abaqus.Model.Model import Model

from src.study_generator.model_input import SimulationConfig


def build_model_and_job(
    cfg: ModelInput,
    sim_config: SimulationConfig,
    model: "Model",
    TEMP_DIR: str,
) -> None:
    """
    Build complete Abaqus/Explicit model and submit job.

    Creates a laminated composite plate model with cohesive interfaces,
    a rigid impactor, applies boundary conditions, and submits the job.

    Args:
        cfg: Model configuration containing geometry, materials, and parameters
        sim_config: Simulation configuration with mesh sizes, time, etc.
        model: Abaqus Model object to build into
        odb_path: Directory path for ODB output file
        log_function: Logging function to use for logging messages
    """

    # ---------------------- Create materials ----------------------
    create_materials(model, cfg)
    elem_ply, elem_impactor = create_element_types()

    # ---------------------- Create geometry ----------------------
    parts = (
        part_ply,
        part_ply_course,
        part_impactor,
    ) = create_geometry(model, cfg, sim_config.coarse_scale)

    # ---------------------- Calculate layer stack ----------------------
    stack_layers = calculate_layer_stack(cfg.ply_angles, cfg.ply_thk, cfg.coh_thk)

    # ---------------------- Assembly ----------------------
    asm = model.rootAssembly

    (
        (lam_parts, lam_course_part, imp_part),
        (lam_instances, lam_course_inst, imp_inst),
    ) = assemble_model(model, asm, parts, stack_layers, cfg)

    for part in lam_parts:
        print("Seeding and meshing part: %s" % part)

    # ---------------------- Assign sections and orientations ----------------------
    assign_sections_and_orientations(
        lam_parts,
        lam_course_part,
        imp_part,
        stack_layers,
        cfg,
        elem_ply,
        elem_impactor,
    )
    #
    ## ---------------------- Mesh ----------------------
    seed_and_mesh_model(
        lam_parts,
        lam_course_part,
        imp_part,
        sim_config,
        cfg,
    )
    #
    # ---------------------- Contact ----------------------
    create_contacts(model, asm, lam_instances, imp_inst, cfg, stack_layers)
    #
    ## ---------------------- Step ----------------------
    create_explicit_step(model, sim_config.time)
    #
    ## ---------------------- Boundary conditions ----------------------
    apply_plate_boundary_conditions(
        model,
        lam_course_inst,
        stack_layers,
        cfg.width,
        cfg.length,
        sim_config.coarse_scale,
    )
    #
    ## ---------------------- Output requests ----------------------
    configure_field_outputs(
        model,
        num_intervals=sim_config.num_output_intervals,
        variables=("CSDMG", "CSQUADSCRT", "CSQUADUCRT", "DMICRTMAX", "S", "U", "EVOL"),
    )
    #
    ## ---------------------- Print model report ----------------------
    print_model_report(
        cfg,
        lam_parts[0.0],
        imp_part,
        lam_course_part,
        sim_config.mesh_coarse,
        sim_config.mesh_refined,
        sim_config.time,
    )

    # ---------------------- Create and submit job ----------------------
    job_name = cfg.job_name()

    # Prepare monitoring parameters
    create_and_submit_job(
        mdb=mdb,
        job_name=job_name,
        model_name="Model-1",
        wait=True,
        TEMP_DIR=TEMP_DIR,
    )
