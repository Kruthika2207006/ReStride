"""Measurement operations for computing residual limb physical properties."""

from typing import Dict, List
import numpy as np
from tools.mesh_loader import LimbMesh


def compute_length(mesh: LimbMesh) -> float:
    """Computes the length of the residual limb along the Z-axis.

    Args:
        mesh: LimbMesh object.

    Returns:
        The length in centimeters.
    """
    z_coords = mesh.vertices[:, 2]
    return float(np.max(z_coords) - np.min(z_coords))


def compute_surface_area(mesh: LimbMesh) -> float:
    """Computes the total surface area of the mesh.

    Args:
        mesh: LimbMesh object.

    Returns:
        Surface area in square centimeters.
    """
    if mesh.o3d_mesh is not None:
        return float(mesh.o3d_mesh.get_surface_area())

    # Pure NumPy fallback
    vA = mesh.vertices[mesh.faces[:, 0]]
    vB = mesh.vertices[mesh.faces[:, 1]]
    vC = mesh.vertices[mesh.faces[:, 2]]
    cross_prod = np.cross(vB - vA, vC - vA)
    face_areas = 0.5 * np.linalg.norm(cross_prod, axis=1)
    return float(np.sum(face_areas))


def compute_volume(mesh: LimbMesh) -> float:
    """Computes the volume of the watertight mesh.

    Args:
        mesh: LimbMesh object.

    Returns:
        Volume in cubic centimeters.
    """
    if mesh.o3d_mesh is not None:
        return float(mesh.o3d_mesh.get_volume())

    # Pure NumPy fallback using signed tetrahedra volumes from origin
    vA = mesh.vertices[mesh.faces[:, 0]]
    vB = mesh.vertices[mesh.faces[:, 1]]
    vC = mesh.vertices[mesh.faces[:, 2]]
    signed_vols = np.sum(vA * np.cross(vB, vC), axis=1) / 6.0
    return float(np.abs(np.sum(signed_vols)))


def compute_bounding_box(mesh: LimbMesh) -> List[float]:
    """Computes the bounding box dimensions.

    Args:
        mesh: LimbMesh object.

    Returns:
        List of [width, depth, height] dimensions in cm.
    """
    min_coords = np.min(mesh.vertices, axis=0)
    max_coords = np.max(mesh.vertices, axis=0)
    return (max_coords - min_coords).tolist()


def compute_slice_perimeter(mesh: LimbMesh, z_height: float) -> float:
    """Computes the exact perimeter of a horizontal cross-section at a given height.

    Args:
        mesh: LimbMesh object.
        z_height: The Z-coordinate plane to slice at.

    Returns:
        The cross-sectional circumference in centimeters.
    """
    # Shift z_height slightly to prevent the slicing plane from aligning exactly with vertex layers,
    # which avoids segment double-counting at grid boundaries.
    z_height = z_height + 1e-5

    # Perturb z slightly if any vertex is exactly equal to z_height to avoid edge case divisions
    vertices = mesh.vertices.copy()
    z = vertices[:, 2]

    # Find triangles intersecting the z-plane
    z_min = z[mesh.faces].min(axis=1)
    z_max = z[mesh.faces].max(axis=1)
    intersecting_faces = mesh.faces[(z_min <= z_height) & (z_max >= z_height)]

    perimeter = 0.0
    for face in intersecting_faces:
        pts = []
        for i in range(3):
            v1_idx = face[i]
            v2_idx = face[(i + 1) % 3]
            v1 = vertices[v1_idx]
            v2 = vertices[v2_idx]

            # Check if edge intersects z_height
            if (v1[2] <= z_height <= v2[2]) or (v2[2] <= z_height <= v1[2]):
                if v1[2] == v2[2]:
                    continue  # Edge lies exactly on plane
                t = (z_height - v1[2]) / (v2[2] - v1[2])
                p_intersect = v1 + t * (v2 - v1)

                # Keep unique points per face intersection (at most 2)
                if not any(np.allclose(p_intersect, p, atol=1e-5) for p in pts):
                    pts.append(p_intersect)

        if len(pts) == 2:
            perimeter += np.linalg.norm(pts[0] - pts[1])

    return float(perimeter)


def compute_cross_sectional_circumferences(
    mesh: LimbMesh,
) -> Dict[str, float]:
    """Computes circumferences at relative heights: 20%, 50%, and 80%.

    Heights are measured from the distal end (lowest Z) to proximal (highest Z).

    Args:
        mesh: LimbMesh object.

    Returns:
        Dictionary mapping percentage height to circumference value in cm.
    """
    z_coords = mesh.vertices[:, 2]
    z_min = np.min(z_coords)
    z_max = np.max(z_coords)
    total_height = z_max - z_min

    percentages = [20, 50, 80]
    circumferences = {}

    for pct in percentages:
        # Calculate target plane height
        z_plane = z_min + (pct / 100.0) * total_height
        circumferences[f"{pct}%"] = compute_slice_perimeter(mesh, z_plane)

    return circumferences


def classify_shape(circumferences: Dict[str, float]) -> str:
    """Classifies residual limb shape based on circumference ratios.

    Args:
        circumferences: Calculated circumferences dict.

    Returns:
        Shape classification string: conical, cylindrical, or bulbous.
    """
    c_20 = circumferences.get("20%", 0.0)
    c_50 = circumferences.get("50%", 0.0)
    c_80 = circumferences.get("80%", 1.0)

    if c_80 == 0.0:
        return "unknown"

    # Bulbous check (distal end is wider than the mid-limb)
    if c_20 > c_50 * 1.03:
        return "bulbous"

    # Conical vs Cylindrical ratio
    ratio = c_20 / c_80
    if ratio < 0.8:
        return "conical"
    else:
        return "cylindrical"
