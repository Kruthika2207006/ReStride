"""Procedural 3D socket generator for transtibial prosthetics using Open3D and NumPy."""

import os
from typing import Dict, Any, Optional
import numpy as np

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False

from tools.mesh_loader import LimbMesh


def base_limb_radius(z: float, L: float, R_avg: float, shape: str) -> float:
    """Computes the base radius of the residual limb profile at height z.

    Args:
        z: Current height from the distal end (0 to L) in mm.
        L: Total length of the residual limb in mm.
        R_avg: Target average radius in mm.
        shape: Limb shape description (conical, cylindrical, bulbous).

    Returns:
        The radius in mm.
    """
    shape_lower = shape.lower()
    if "conical" in shape_lower:
        # Wider proximal opening, narrow distal end
        return R_avg * (0.6 + 0.8 * (z / L))
    elif "cylindrical" in shape_lower:
        # Constant diameter
        return R_avg * 1.0
    elif "bulbous" in shape_lower:
        # Bulged distal region: wider at bottom, narrows in middle, flares at top
        return R_avg * (0.8 + 0.4 * (z / L) + 0.3 * np.cos(1.5 * np.pi * z / L) * (1.0 - z / L))
    else:
        # Default to conical
        return R_avg * (0.6 + 0.8 * (z / L))


def gaussian_relief(
    z: float,
    theta: float,
    z_center: float,
    theta_center: float,
    z_sigma: float,
    theta_sigma: float,
    amplitude: float,
) -> float:
    """Computes a localized Gaussian radial offset/relief.

    Args:
        z: Height in mm.
        theta: Angle in radians.
        z_center: Center height in mm.
        theta_center: Center angle in radians.
        z_sigma: Width along Z axis in mm.
        theta_sigma: Width along theta axis in radians.
        amplitude: Peak offset in mm.

    Returns:
        Radial offset value in mm.
    """
    d_theta = np.arctan2(np.sin(theta - theta_center), np.cos(theta - theta_center))
    return amplitude * np.exp(-((z - z_center) ** 2) / (2.0 * z_sigma ** 2) - (d_theta ** 2) / (2.0 * theta_sigma ** 2))


def line_relief(
    z: float,
    theta: float,
    z_start: float,
    z_end: float,
    theta_center: float,
    z_sigma: float,
    theta_sigma: float,
    amplitude: float,
) -> float:
    """Computes a radial offset/relief along a vertical line segment (e.g. tibial crest).

    Args:
        z: Height in mm.
        theta: Angle in radians.
        z_start: Start height in mm.
        z_end: End height in mm.
        theta_center: Angle in radians.
        z_sigma: Falloff width along Z past the segment ends.
        theta_sigma: Width along theta axis in radians.
        amplitude: Peak offset in mm.

    Returns:
        Radial offset value in mm.
    """
    d_theta = np.arctan2(np.sin(theta - theta_center), np.cos(theta - theta_center))
    if z < z_start:
        d_z = z_start - z
    elif z > z_end:
        d_z = z - z_end
    else:
        d_z = 0.0
    return amplitude * np.exp(-((d_z) ** 2) / (2.0 * z_sigma ** 2) - (d_theta ** 2) / (2.0 * theta_sigma ** 2))


def generate_procedural_grid(shape: str, length_mm: float, R_avg: float, Nz: int, Ntheta: int) -> np.ndarray:
    """Generates a structured grid (Nz x Ntheta x 3) of the mathematical limb profile.

    Args:
        shape: Shape type (Conical, Cylindrical, Bulbous).
        length_mm: Length in mm.
        R_avg: Average radius in mm.
        Nz: Number of slices.
        Ntheta: Number of angular points.

    Returns:
        Array of shape (Nz, Ntheta, 3).
    """
    grid = np.zeros((Nz, Ntheta, 3))
    for i in range(Nz):
        u = i / (Nz - 1)
        z = u * length_mm
        for j in range(Ntheta):
            theta = j * (2.0 * np.pi / Ntheta)
            r = base_limb_radius(z, length_mm, R_avg, shape)

            # Apply anatomical shape factor to make it look like a realistic leg:
            # - Anterior (90 deg): unchanged (1.0)
            # - Posterior (270 deg): flatter (factor 0.92)
            # - Lateral (0 deg): narrower (factor 0.95)
            # - Medial (180 deg): wider (factor 1.05)
            f_asym = 1.0 - 0.05 * np.cos(theta) - 0.08 * max(0.0, -np.sin(theta))
            r = r * f_asym

            grid[i, j, 0] = r * np.cos(theta)
            grid[i, j, 1] = r * np.sin(theta)
            grid[i, j, 2] = z
    return grid


def resample_mesh_to_grid(mesh: LimbMesh, Nz: int, Ntheta: int) -> np.ndarray:
    """Resamples an unstructured limb mesh into a structured cylindrical grid of (Nz x Ntheta x 3).

    Args:
        mesh: LimbMesh wrapper object.
        Nz: Target Z slices.
        Ntheta: Target angular resolution.

    Returns:
        Structured grid of shape (Nz, Ntheta, 3).
    """
    vertices = mesh.vertices
    z_coords = vertices[:, 2]
    z_min = float(np.min(z_coords))
    z_max = float(np.max(z_coords))
    L = z_max - z_min

    grid = np.zeros((Nz, Ntheta, 3))

    for i in range(Nz):
        z_plane = z_min + (i / (Nz - 1)) * L
        # Filter vertices near this plane height
        tol = max(L / (2.0 * Nz), 1.0)
        idx = np.where(np.abs(z_coords - z_plane) < tol)[0]
        if len(idx) < 3:
            idx = np.argsort(np.abs(z_coords - z_plane))[:10]

        pts = vertices[idx]
        angles = np.arctan2(pts[:, 1], pts[:, 0])

        for j in range(Ntheta):
            target_theta = j * (2.0 * np.pi / Ntheta)
            diff = np.arctan2(np.sin(angles - target_theta), np.cos(angles - target_theta))
            closest_idx = int(np.argmin(np.abs(diff)))

            r = float(np.linalg.norm(pts[closest_idx, :2]))
            grid[i, j, 0] = r * np.cos(target_theta)
            grid[i, j, 1] = r * np.sin(target_theta)
            grid[i, j, 2] = z_plane - z_min

    return grid


def generate_socket_mesh_from_grid(grid: np.ndarray, rec: Dict[str, Any]) -> "o3d.geometry.TriangleMesh":
    """Procedurally generates a watertight 3D socket mesh from a structured limb grid.

    Args:
        grid: Array of shape (Nz, Ntheta, 3) representing the limb profile.
        rec: Recommendation parameters dictionary.

    Returns:
        Open3D TriangleMesh.
    """
    if not HAS_OPEN3D:
        raise ImportError("Open3D is required to generate the 3D socket mesh.")

    Nz, Ntheta, _ = grid.shape

    # Extract recommendation values
    socket_type = rec.get("socket_type", "TSB")
    suspension = rec.get("suspension", "Suction")
    wall_thickness = float(rec.get("wall_thickness_mm", 4.0))
    radial_expansion = float(rec.get("radial_expansion_mm", 1.0))
    distal_clearance = float(rec.get("distal_clearance_mm", 4.0))

    # Length of the grid along Z axis
    z_coords = grid[:, :, 2]
    L = float(np.max(z_coords) - np.min(z_coords))

    # We will build two grids: inner_grid and outer_grid
    inner_grid = np.zeros_like(grid)
    outer_grid = np.zeros_like(grid)

    # Determine bottom height of outer wall
    z_start_outer = -20.0 if "pin" in suspension.lower() else 0.0

    # 1. Generate modified inner grid (from distal_clearance to contoured proximal trimline)
    for j in range(Ntheta):
        theta = j * (2.0 * np.pi / Ntheta)
        # Contoured top trimline (high at medial/lateral, popliteal cutout at posterior)
        h_trim_val = 8.0 * np.cos(2.0 * theta) + 4.0 * np.sin(theta)
        L_theta = L + h_trim_val

        for i in range(Nz):
            u = i / (Nz - 1)
            # Inner cavity Z goes from distal_clearance to L_theta
            z_inner = distal_clearance + u * (L_theta - distal_clearance)

            # Get index in the input grid closest to z_inner's projection (clamped to original [0, L])
            z_eval_base = min(max(0.0, z_inner), L)
            idx_z_in = min(int(round((z_eval_base / L) * (Nz - 1))), Nz - 1)

            pt = grid[idx_z_in, j]
            r_base = float(np.linalg.norm(pt[:2]))

            # Apply radial expansion
            r_inner = r_base + radial_expansion

            # Apply PTB specific relief features
            if "ptb" in socket_type.lower():
                # A. Patellar Tendon Relief (anterior, theta = 90 deg, z_center = 0.8 L)
                r_inner += gaussian_relief(z_inner, theta, 0.8 * L, np.pi / 2.0, 0.08 * L, 0.26, 3.0)

                # B. Tibial Crest Relief (anterior-lateral, theta = 60 deg, z_start = 0.3 L, z_end = 0.7 L)
                r_inner += line_relief(z_inner, theta, 0.3 * L, 0.7 * L, 60.0 * np.pi / 180.0, 0.06 * L, 0.17, 3.5)

                # C. Fibular Head Relief (lateral-proximal, theta = 315 deg, z_center = 0.75 L)
                r_inner += gaussian_relief(z_inner, theta, 0.75 * L, 315.0 * np.pi / 180.0, 0.06 * L, 0.21, 4.0)

            # Apply brim flare near proximal opening
            if z_inner > 0.85 * L:
                t = (z_inner - 0.85 * L) / (0.15 * L)
                flare_amp = 5.0 if "suction" in suspension.lower() else 3.0
                r_inner += flare_amp * (t ** 2)

            inner_grid[i, j, 0] = r_inner * np.cos(theta)
            inner_grid[i, j, 1] = r_inner * np.sin(theta)
            inner_grid[i, j, 2] = z_inner

    # 2. Generate modified outer grid (from z_start_outer to contoured proximal trimline)
    for j in range(Ntheta):
        theta = j * (2.0 * np.pi / Ntheta)
        h_trim_val = 8.0 * np.cos(2.0 * theta) + 4.0 * np.sin(theta)
        L_theta = L + h_trim_val

        for i in range(Nz):
            u = i / (Nz - 1)
            z_outer = z_start_outer + u * (L_theta - z_start_outer)

            # To find outer radius, evaluate inner radius at z_outer (clamped to >= distal_clearance)
            z_eval = max(distal_clearance, z_outer)
            scale_factor = (z_eval - distal_clearance) / (L_theta - distal_clearance) if L_theta > distal_clearance else 0.0
            idx_z_in = min(int(round(scale_factor * (Nz - 1))), Nz - 1)

            pt_inner = inner_grid[idx_z_in, j]
            r_inner_val = float(np.linalg.norm(pt_inner[:2]))

            r_outer = r_inner_val + wall_thickness

            # Apply sealing lip for Vacuum suspension (at z = 0.9 L)
            if "vacuum" in suspension.lower() and z_outer >= 0.0:
                r_outer += 2.0 * np.exp(-((z_outer - 0.9 * L) ** 2) / (2.0 * 2.0 ** 2))

            # Apply Pin Lock distal housing adapter (at z < 0)
            if z_outer < 0.0:
                # Smoothly blend from 25.0 mm at z = -20 to main bottom outer radius at z = 0
                r_main_bottom = float(np.linalg.norm(inner_grid[0, j][:2])) + wall_thickness
                t_blend = (z_outer + 20.0) / 20.0
                r_outer = 25.0 + (r_main_bottom - 25.0) * t_blend

            outer_grid[i, j, 0] = r_outer * np.cos(theta)
            outer_grid[i, j, 1] = r_outer * np.sin(theta)
            outer_grid[i, j, 2] = z_outer

    # Assemble Vertices
    vertices = []
    # 0. Inner cap center vertex
    vertices.append([0.0, 0.0, distal_clearance])

    # 1 to Nz*Ntheta: Inner grid vertices
    for i in range(Nz):
        for j in range(Ntheta):
            vertices.append(inner_grid[i, j].tolist())

    # Nz*Ntheta + 1: Outer cap center vertex
    C_outer_idx = 1 + Nz * Ntheta
    vertices.append([0.0, 0.0, z_start_outer])

    # C_outer_idx + 1 onwards: Outer grid vertices
    for i in range(Nz):
        for j in range(Ntheta):
            vertices.append(outer_grid[i, j].tolist())

    vertices_np = np.array(vertices, dtype=np.float64)

    # Assemble Triangles
    triangles = []
    N = Ntheta

    # A. Inner bottom cap (winding order: inward, i.e., normal points in +Z)
    for j in range(N):
        vj = 1 + j
        vnext = 1 + (j + 1) % N
        triangles.append([0, vj, vnext])

    # B. Inner cylindrical wall (winding order: inward, i.e., normal points towards axis)
    for i in range(Nz - 1):
        for j in range(N):
            A = 1 + i * N + j
            B = 1 + i * N + (j + 1) % N
            C = 1 + (i + 1) * N + (j + 1) % N
            D = 1 + (i + 1) * N + j
            triangles.append([A, D, C])
            triangles.append([A, C, B])

    # C. Outer bottom cap (winding order: outward, i.e., normal points in -Z)
    for j in range(N):
        wj = C_outer_idx + 1 + j
        wnext = C_outer_idx + 1 + (j + 1) % N
        triangles.append([C_outer_idx, wnext, wj])

    # D. Outer cylindrical wall (winding order: outward, i.e., normal points away from axis)
    for i in range(Nz - 1):
        for j in range(N):
            A = C_outer_idx + 1 + i * N + j
            B = C_outer_idx + 1 + i * N + (j + 1) % N
            C = C_outer_idx + 1 + (i + 1) * N + (j + 1) % N
            D = C_outer_idx + 1 + (i + 1) * N + j
            triangles.append([A, C, D])
            triangles.append([A, B, C])

    # E. Top brim bridge (winding order: upward, normal points in +Z)
    for j in range(N):
        Ij = 1 + (Nz - 1) * N + j
        Inext = 1 + (Nz - 1) * N + (j + 1) % N
        Oj = C_outer_idx + 1 + (Nz - 1) * N + j
        Onext = C_outer_idx + 1 + (Nz - 1) * N + (j + 1) % N
        triangles.append([Ij, Oj, Inext])
        triangles.append([Oj, Onext, Inext])

    triangles_np = np.array(triangles, dtype=np.int32)

    # Create Open3D mesh object
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(vertices_np)
    mesh.triangles = o3d.utility.Vector3iVector(triangles_np)

    # Auto-generate normal arrays
    mesh.compute_vertex_normals()
    mesh.compute_triangle_normals()

    return mesh


def generate_socket(recommendation: Dict[str, Any], limb_mesh: Optional[LimbMesh] = None) -> "o3d.geometry.TriangleMesh":
    """Main generation routine. Takes a recommendation config (and optional scan mesh) and returns the completed socket.

    Args:
        recommendation: Dict containing estimated_length_cm, average_width_ratio, etc.
        limb_mesh: Optional raw scan input. If omitted, procedural profile is generated.

    Returns:
        An Open3D TriangleMesh.
    """
    Nz = 100
    Ntheta = 72

    if limb_mesh is not None:
        # Extract profile from scan
        grid = resample_mesh_to_grid(limb_mesh, Nz, Ntheta)
    else:
        # Generate procedural mathematical limb profile
        length_cm = float(recommendation.get("estimated_length_cm", 15.0))
        length_mm = length_cm * 10.0
        width_ratio = float(recommendation.get("average_width_ratio", 2.173))
        D_avg = (length_cm / width_ratio) * 10.0
        R_avg = D_avg / 2.0
        shape = recommendation.get("residual_limb_shape", "Conical")

        grid = generate_procedural_grid(shape, length_mm, R_avg, Nz, Ntheta)

    # Generate the socket geometry from grid
    return generate_socket_mesh_from_grid(grid, recommendation)
