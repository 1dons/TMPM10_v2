# model_input.py
"""
Data classes for composite impact simulation configurations.

Defines immutable dataclasses for:
- SimulationConfig: Simulation parameters (mesh, time, etc.)
- MaterialSetup: Lamina and cohesive material properties
- ModelInput: Complete simulation configuration including geometry, layup, and impact parameters
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any
import os


@dataclass(frozen=True)
class SimulationConfig:
    """
    Simulation parameters for mesh sizing, time steps, and post-processing.

    Attributes:
        time: Total simulation time in seconds
        mesh_refined: Element size for refined (impact) region in mm
        mesh_coarse: Element size for coarse (outer) region in mm
        coarse_scale: Scale factor for coarse region size (default 2.0)
        num_output_intervals: Number of field output intervals (default 250)
    """

    time: float
    mesh_refined: float
    mesh_coarse: float
    coarse_scale: float = 2.0
    num_output_intervals: int = 250

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SimulationConfig":
        """
        Create SimulationConfig from a dictionary.

        Args:
            d: Dictionary containing simulation parameters

        Returns:
            SimulationConfig: Initialized simulation configuration
        """
        return SimulationConfig(
            time=float(d.get("time", 0.008)),
            mesh_refined=float(d.get("mesh_refined", 1)),
            mesh_coarse=float(d.get("mesh_coarse", 2)),
            coarse_scale=float(d.get("coarse_scale", 2.0)),
            num_output_intervals=int(d.get("num_output_intervals", 250)),
        )


@dataclass(frozen=True)
class MaterialSetup:
    """
    Material properties for lamina (ply) and cohesive interface layers.

    Attributes:
        Lamina properties (MPa, ton/mm³):
            E1, E2, E3: Elastic moduli in three principal directions
            NU12, NU13, NU23: Poisson's ratios
            G12, G13, G23: Shear moduli
            rho_lam: Lamina density (ton/mm³)

        Cohesive interface properties:
            En, G1, G2: Normal and shear elastic stiffnesses (MPa/mm)
            N, S1, S2: Peak normal and shear tractions (MPa)
            eta: BK (Benzeggagh-Kenane) mixed-mode parameter
            GIc, GIIc, GIIIc: Mode I, II, III fracture energies (N/mm)
            rho_coh: Cohesive layer density (ton/mm³)
    """

    # Lamina (MPa, ton/mm^3)
    E1: float
    E2: float
    E3: float
    NU12: float
    NU13: float
    NU23: float
    G12: float
    G13: float
    G23: float
    rho_lam: float
    # Cohesive
    En: float
    G1: float
    G2: float
    N: float
    S1: float
    S2: float
    eta: float
    GIc: float
    GIIc: float
    GIIIc: float
    rho_coh: float

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "MaterialSetup":
        """
        Create MaterialSetup from a dictionary.

        Args:
            d: Dictionary containing all material property keys

        Returns:
            MaterialSetup: Initialized material properties object
        """
        return MaterialSetup(
            E1=d["E1"],
            E2=d["E2"],
            E3=d["E3"],
            NU12=d["NU12"],
            NU13=d["NU13"],
            NU23=d["NU23"],
            G12=d["G12"],
            G13=d["G13"],
            G23=d["G23"],
            rho_lam=d["rho_lam"],
            En=d["En"],
            G1=d["G1"],
            G2=d["G2"],
            N=d["N"],
            S1=d["S1"],
            S2=d["S2"],
            eta=d["eta"],
            GIc=d["GIc"],
            GIIc=d["GIIc"],
            GIIIc=d["GIIIc"],
            rho_coh=d["rho_coh"],
        )


@dataclass(frozen=True)
class ModelInput:
    """
    Complete configuration for a single composite impact simulation.

    Attributes:
        uid: Unique identifier for this configuration
        study: Study name (e.g., 'parameter_study')
        created_at: ISO timestamp of creation
        units: Unit system (e.g., 'mm-s-ton-MPa')
        width: Plate width in mm
        length: Plate length in mm
        ply_angles: List of ply angles in degrees, from bottom to top
        ply_thk: Ply thickness in mm
        coh_thk: Cohesive layer thickness in mm
        imp_radius: Impactor radius in mm
        imp_mass: Impactor mass in tons
        imp_speed: Impact velocity in mm/s
        material_name: Name of the material preset
        material: Material properties object

    Properties (computed):
        n_ply: Number of plies
        n_coh: Number of cohesive layers (based on angle changes)
        plate_T: Total plate thickness in mm
        imp_energy_J: Impact kinetic energy in Joules
    """

    uid: str
    study: str
    created_at: str
    units: str
    width: float
    length: float
    ply_angles: List[int]
    ply_thk: float
    coh_thk: float
    imp_radius: float
    imp_mass: float
    imp_speed: float
    material_name: str
    material: MaterialSetup

    @property
    def n_ply(self) -> int:
        """Number of plies in the layup."""
        return len(self.ply_angles)

    @property
    def n_coh(self) -> int:
        """
        Number of cohesive layers (interfaces between plies with different angles).

        Cohesive layers are inserted between adjacent plies that have different
        fiber orientations to capture delamination.
        """
        ang = self.ply_angles
        return sum(1 for i in range(len(ang) - 1) if ang[i] != ang[i + 1])

    @property
    def plate_T(self) -> float:
        """Total plate thickness in mm (plies + cohesive layers)."""
        return self.n_ply * self.ply_thk

    @property
    def imp_energy_J(self) -> float:
        """Impact kinetic energy in Joules (0.5 * m * v²)."""
        m_kg = self.imp_mass * 1000.0
        v_m_s = self.imp_speed / 1000.0
        return 0.5 * m_kg * v_m_s * v_m_s

    def job_name(self) -> str:
        """
        Generate unique job name for this configuration.

        Returns:
            Job name string in format: {study}_{uid}
        """
        return f"{self.study}_{self.uid}"

    def create_txt_summary(self, filepath: str) -> None:
        """
        Write a human-readable summary of the configuration to a text file.

        Args:
            filepath: Path where the summary text file will be written
        """
        txt_file = os.path.join(filepath, "config_summary.txt")
        with open(txt_file, "w") as f:
            f.write("Job Summary\n")
            f.write("===========\n")
            f.write(f"Job Name: {self.job_name()}\n")

            f.write("\nPlate Data:\n")
            f.write("===========\n")
            f.write(f"Ply Angles: {self.ply_angles}\n")
            f.write(f"Ply Thickness (mm): {self.ply_thk:.3f}\n")
            f.write(f"Cohesive Thickness (mm): {self.coh_thk:.3f}\n")
            f.write(f"Number of Plies: {self.n_ply}\n")
            f.write(f"Number of Cohesive Layers: {self.n_coh}\n")
            f.write(f"Plate Thickness (mm): {self.plate_T:.3f}\n")

            f.write("\nImpactor Data:\n")
            f.write("===========\n")
            f.write(f"Impact Radius (mm): {self.imp_radius:.1f}\n")
            f.write(f"Impact Mass (kg): {self.imp_mass * 1e3:.3f}\n")
            f.write(f"Impact Speed (m/s): {self.imp_speed * 1e-3:.1f}\n")
            f.write(f"Impact Energy (J): {self.imp_energy_J:.1f}\n")
            # TODO: add more details as needed
