"""Verification script to test the Geometry Agent with a synthetic STL file."""

import os
import sys
import struct
from typing import Dict
import numpy as np

# Add workspace directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.request import (
    SocketRecommendationRequest,
    ResidualLimbDetails,
    PatientClinicalHistory,
)
from agents.geometry_agent import GeometryAgent


def generate_conical_limb_stl(file_path: str) -> Dict[str, float]:
    """Generates a synthetic conical limb STL file and returns exact theoretical values.

    Cone Frustum Specs:
    - Height: 15.0 cm (from Z=0 to Z=15)
    - Proximal Radius (Z=15): 5.0 cm (Circumference = 31.42 cm)
    - Distal Radius (Z=0): 3.0 cm (Circumference = 18.85 cm)
    """
    height = 15.0
    r_distal = 3.0
    r_proximal = 5.0
    num_segments = 32
    num_height_steps = 15

    vertices = []
    # Bottom/distal center cap vertex (Z=0)
    vertices.append([0.0, 0.0, 0.0])  # Index 0
    # Top/proximal center cap vertex (Z=15)
    vertices.append([0.0, 0.0, height])  # Index 1

    # Generate rings of vertices
    for h in range(num_height_steps + 1):
        z = (h / num_height_steps) * height
        # Linear interpolation of radius from distal (Z=0) to proximal (Z=15)
        r = r_distal + (h / num_height_steps) * (r_proximal - r_distal)
        for s in range(num_segments):
            theta = 2.0 * np.pi * s / num_segments
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            vertices.append([x, y, z])

    faces = []

    # Bottom cap faces (distal center is index 0)
    for s in range(num_segments):
        v1 = 2 + s
        v2 = 2 + (s + 1) % num_segments
        faces.append([0, v2, v1])

    # Top cap faces (proximal center is index 1)
    last_ring_start = 2 + num_height_steps * num_segments
    for s in range(num_segments):
        v1 = last_ring_start + s
        v2 = last_ring_start + (s + 1) % num_segments
        faces.append([1, v1, v2])

    # Side wall faces
    for h in range(num_height_steps):
        ring_curr = 2 + h * num_segments
        ring_next = 2 + (h + 1) * num_segments
        for s in range(num_segments):
            c1 = ring_curr + s
            c2 = ring_curr + (s + 1) % num_segments
            n1 = ring_next + s
            n2 = ring_next + (s + 1) % num_segments

            # CCW orientation normals pointing outward
            faces.append([c1, c2, n1])
            faces.append([c2, n2, n1])

    # Ensure parent dir exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Write binary STL
    with open(file_path, "wb") as f:
        f.write(b"Synthetic Conical Limb Scan" + b"\0" * 53)  # 80-byte header
        f.write(struct.pack("<I", len(faces)))
        for face in faces:
            # Compute triangle normal
            v0 = np.array(vertices[face[0]])
            v1 = np.array(vertices[face[1]])
            v2 = np.array(vertices[face[2]])
            normal = np.cross(v1 - v0, v2 - v0)
            norm = np.linalg.norm(normal)
            if norm > 0:
                normal /= norm
            else:
                normal = np.array([0.0, 0.0, 0.0])

            f.write(struct.pack("<fff", *normal))
            f.write(struct.pack("<fff", *v0))
            f.write(struct.pack("<fff", *v1))
            f.write(struct.pack("<fff", *v2))
            f.write(struct.pack("<H", 0))

    # Calculate theoretical values (frustum of a cone)
    theoretical_volume = (
        (1.0 / 3.0)
        * np.pi
        * height
        * (r_proximal**2 + r_distal**2 + r_proximal * r_distal)
    )
    slant_height = np.sqrt((r_proximal - r_distal) ** 2 + height**2)
    theoretical_area = (
        np.pi * (r_proximal + r_distal) * slant_height
        + np.pi * r_proximal**2
        + np.pi * r_distal**2
    )

    return {
        "length": height,
        "volume": theoretical_volume,
        "area": theoretical_area,
        "proximal_circumference": 2.0 * np.pi * r_proximal,
        "distal_circumference": 2.0 * np.pi * r_distal,
    }


def verify_geometry_agent():
    """Runs the test harness to load and verify the Geometry Agent."""
    print("=== Geometry Agent Verification ===")

    stl_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "scratch_limb_mesh.stl")
    )

    # 1. Generate mesh
    print(f"Generating synthetic STL mesh at: {stl_path} ...")
    theoretical = generate_conical_limb_stl(stl_path)

    # 2. Setup mock request referencing this STL file
    request = SocketRecommendationRequest(
        patient_id="PAT-STL-TEST",
        age=45,
        weight_kg=85.0,
        activity_level="K3",
        amputation_level="transtibial",
        limb_details=ResidualLimbDetails(
            shape="conical",
            length_cm=15.0,
            proximal_circumference_cm=31.42,
            mid_limb_circumference_cm=25.13,
            distal_circumference_cm=18.85,
            skin_condition="healthy",
            prominent_bones=False,
            additional_notes="Testing STL file loading.",
        ),
        clinical_history=PatientClinicalHistory(
            amputation_reason="trauma",
            has_diabetes=False,
            has_neuropathy=False,
            volume_fluctuations=False,
        ),
        stl_file_path=stl_path,
    )

    state = {
        "request": request,
        "geometry_analysis_results": {},
        "errors": [],
    }

    # 3. Instantiate and execute the geometry agent
    agent = GeometryAgent()
    print("Executing GeometryAgent.run()...")
    output = agent.run(state)

    # Clean up generated STL
    if os.path.exists(stl_path):
        os.remove(stl_path)

    if "errors" in output and len(output["errors"]) > len(state["errors"]):
        print(f"[-] Execution failed with errors: {output['errors']}")
        sys.exit(1)

    geom = output["geometry_analysis_results"]

    print("\n--- Theoretical vs Computed Metrics ---")
    print(
        f"Limb Length:        Theory={theoretical['length']:.2f} cm | Computed={geom['limb_length_cm']:.2f} cm"
    )
    print(
        f"Mesh Surface Area:  Theory={theoretical['area']:.2f} cm2 | Computed={geom['surface_area_cm2']:.2f} cm2"
    )
    print(
        f"Mesh Volume:        Theory={theoretical['volume']:.2f} cm3 | Computed={geom['volume_cm3']:.2f} cm3"
    )
    print(f"Bounding Box Dims:  {geom['bounding_box_dims']}")
    print(
        f"Watertight Status:  Computed={geom['is_watertight']} (Mesh status: {geom['mesh_status']})"
    )
    print(f"Shape Descriptor:   Computed={geom['shape_descriptor']}")
    print(f"Circumferences:     {geom['cross_sectional_circumferences']}")

    # 4. Assertions to confirm correctness
    # Tolerances are small because a 32-segment mesh approximation has slightly less volume/area than a perfect cone.
    assert (
        abs(geom["limb_length_cm"] - theoretical["length"]) < 0.1
    ), "Length mismatch!"
    assert (
        abs(geom["surface_area_cm2"] - theoretical["area"]) / theoretical["area"]
        < 0.05
    ), "Surface area error too high!"
    assert (
        abs(geom["volume_cm3"] - theoretical["volume"]) / theoretical["volume"]
        < 0.05
    ), "Volume error too high!"
    assert geom["is_watertight"], "Mesh should be watertight!"
    assert geom["shape_descriptor"] == "conical", "Shape classification mismatch!"

    print("\n[+] Geometry Agent Verification PASSED!")


if __name__ == "__main__":
    verify_geometry_agent()
