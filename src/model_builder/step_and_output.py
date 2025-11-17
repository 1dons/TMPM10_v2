"""
Step and output request definitions for composite impact simulations.

Handles:
- Explicit dynamics step creation
- Field output requests
- History output requests
"""

from typing import TYPE_CHECKING, Tuple

from abaqus import *
from abaqusConstants import *
from step import *

if TYPE_CHECKING:
    from abaqus.Model.Model import Model


def create_explicit_step(
    model: "Model", simulation_time: float, description: str = ""
) -> None:
    """
    Create explicit dynamics step for impact simulation.

    Args:
        model: Abaqus Model object
        simulation_time: Total simulation time in seconds
        description: Optional step description
    """
    model.ExplicitDynamicsStep(
        name="ImpactStep",
        previous="Initial",
        timePeriod=simulation_time,
        description=description,
    )


def configure_field_outputs(
    model: "Model",
    num_intervals: int = 250,
    variables: Tuple[str, ...] = ("SDEG", "S", "U", "EVOL"),
) -> None:
    """
    Configure field output requests for the simulation.

    Args:
        model: Abaqus Model object
        num_intervals: Number of output intervals (default 250)
        variables: Tuple of field output variable names
            Default: ("SDEG", "S", "U", "EVOL")
            - SDEG: Scalar stiffness degradation
            - S: Stresses
            - U: Displacements
            - EVOL: Element volume
    """
    model.fieldOutputRequests["F-Output-1"].setValues(
        numIntervals=num_intervals,
        variables=variables,
    )
