"""Mesh loader for loading, validating, and repairing STL mesh data."""

import os
import struct
from typing import Tuple, Optional, List, Any
import numpy as np

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False


class LimbMesh:
    """Wrapper class for residual limb 3D mesh representation.

    Works with Open3D if available, otherwise falls back to pure NumPy representation.
    """

    def __init__(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        o3d_mesh: Optional[Any] = None,
    ):
        """Initializes the LimbMesh wrapper.

        Args:
            vertices: NumPy array of shape (N, 3) representing mesh vertices.
            faces: NumPy array of shape (M, 3) representing triangle indices.
            o3d_mesh: The underlying Open3D TriangleMesh object if available.
        """
        self.vertices = vertices
        self.faces = faces
        self.o3d_mesh = o3d_mesh

    @property
    def num_vertices(self) -> int:
        """Returns the number of vertices."""
        return len(self.vertices)

    @property
    def num_triangles(self) -> int:
        """Returns the number of triangles/faces."""
        return len(self.faces)


class MeshLoader:
    """Handles STL loading, validation, and standard repair procedures."""

    @staticmethod
    def load_stl(file_path: str) -> LimbMesh:
        """Loads an STL file (ASCII or Binary) into a LimbMesh object.

        Args:
            file_path: Path to the STL file.

        Returns:
            A LimbMesh object.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"STL file not found: {file_path}")

        # Attempt to load using Open3D if available
        if HAS_OPEN3D:
            try:
                o3d_mesh = o3d.io.read_triangle_mesh(file_path)
                vertices = np.asarray(o3d_mesh.vertices, dtype=np.float32)
                faces = np.asarray(o3d_mesh.triangles, dtype=np.int32)
                return LimbMesh(vertices, faces, o3d_mesh)
            except Exception as e:
                # If Open3D fails to load, fall back to pure Python loader
                pass

        # Fallback pure-python parser (supports both binary and ASCII formats)
        vertices, faces = MeshLoader._parse_stl_pure_python(file_path)
        return LimbMesh(vertices, faces)

    @staticmethod
    def validate_and_repair(
        mesh: LimbMesh,
    ) -> Tuple[LimbMesh, bool, str, List[str]]:
        """Checks mesh integrity and applies basic repairs if needed.

        Args:
            mesh: LimbMesh to check and repair.

        Returns:
            A tuple of:
            - Repaired LimbMesh
            - is_watertight (bool)
            - mesh_status (str)
            - errors/warnings list
        """
        errors = []
        is_watertight = False

        if mesh.o3d_mesh is not None and HAS_OPEN3D:
            o3d_mesh = mesh.o3d_mesh
            # Run Open3D cleaning operations
            o3d_mesh.remove_duplicated_vertices()
            o3d_mesh.remove_duplicated_triangles()
            o3d_mesh.remove_degenerate_triangles()
            o3d_mesh.remove_unreferenced_vertices()

            is_edge_manifold = o3d_mesh.is_edge_manifold()
            is_vertex_manifold = o3d_mesh.is_vertex_manifold()
            # Retrieve boundary/non-manifold edges; if empty, there are no open boundary edges
            boundary_edges = o3d_mesh.get_non_manifold_edges(allow_boundary_edges=False)
            has_no_boundary = len(boundary_edges) == 0

            is_watertight = is_edge_manifold and is_vertex_manifold and has_no_boundary
            mesh_status = "Clean" if is_watertight else "Unrepairable Holes"
            if not is_watertight:
                if not is_edge_manifold:
                    errors.append("Mesh is not edge manifold.")
                if not is_vertex_manifold:
                    errors.append("Mesh is not vertex manifold.")
                if not has_no_boundary:
                    errors.append(
                        "Mesh contains open boundaries / holes and is not watertight."
                    )

            # Update the numpy arrays
            vertices = np.asarray(o3d_mesh.vertices, dtype=np.float32)
            faces = np.asarray(o3d_mesh.triangles, dtype=np.int32)
            repaired_mesh = LimbMesh(vertices, faces, o3d_mesh)
            return repaired_mesh, is_watertight, mesh_status, errors

        # Pure-python validation and repair fallback
        # 1. Clean degenerate faces (faces where vertices coincide)
        valid_faces = []
        for f in mesh.faces:
            if len(set(f)) == 3:
                valid_faces.append(f)
        faces_cleaned = np.array(valid_faces, dtype=np.int32)

        # 2. Check watertightness (every edge in a manifold closed mesh must be shared by exactly 2 faces)
        from collections import Counter

        edges = []
        for f in faces_cleaned:
            f_sorted = sorted(f)
            edges.append((f_sorted[0], f_sorted[1]))
            edges.append((f_sorted[1], f_sorted[2]))
            edges.append((f_sorted[0], f_sorted[2]))

        edge_counts = Counter(edges)
        is_watertight = len(edge_counts) > 0 and all(
            count == 2 for count in edge_counts.values()
        )

        mesh_status = "Clean" if is_watertight else "Has Open Edges"
        if not is_watertight:
            errors.append(
                "Mesh is open / non-watertight (boundary edges detected)."
            )

        repaired_mesh = LimbMesh(mesh.vertices, faces_cleaned)
        return repaired_mesh, is_watertight, mesh_status, errors

    @staticmethod
    def _parse_stl_pure_python(
        file_path: str,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Parses STL files (binary or ASCII) in pure Python."""
        with open(file_path, "rb") as f:
            header = f.read(80)
            num_triangles_bytes = f.read(4)
            if len(num_triangles_bytes) < 4:
                return MeshLoader._parse_ascii_stl(file_path)

            num_triangles = struct.unpack("<I", num_triangles_bytes)[0]

            # Confirm file size matches binary STL format
            f.seek(0, 2)
            file_size = f.tell()
            expected_size = 80 + 4 + num_triangles * 50

            if file_size == expected_size:
                f.seek(84)
                vertices = []
                faces = []
                vertex_map = {}
                for _ in range(num_triangles):
                    triangle_data = f.read(50)
                    if len(triangle_data) < 50:
                        break
                    # Unpack 12 floats (normal + 3 vertices) and 1 uint16 (attributes)
                    data = struct.unpack("<ffffffffffffH", triangle_data)
                    # Vertices are indices 3-5, 6-8, 9-11
                    v1 = (
                        round(data[3], 6),
                        round(data[4], 6),
                        round(data[5], 6),
                    )
                    v2 = (
                        round(data[6], 6),
                        round(data[7], 6),
                        round(data[8], 6),
                    )
                    v3 = (
                        round(data[9], 6),
                        round(data[10], 6),
                        round(data[11], 6),
                    )

                    face_indices = []
                    for v in (v1, v2, v3):
                        if v not in vertex_map:
                            vertex_map[v] = len(vertex_map)
                            vertices.append(v)
                        face_indices.append(vertex_map[v])
                    faces.append(face_indices)
                return np.array(vertices, dtype=np.float32), np.array(
                    faces, dtype=np.int32
                )
            else:
                return MeshLoader._parse_ascii_stl(file_path)

    @staticmethod
    def _parse_ascii_stl(file_path: str) -> Tuple[np.ndarray, np.ndarray]:
        """Parses ASCII STL file."""
        vertices = []
        faces = []
        vertex_map = {}

        with open(file_path, "r", errors="ignore") as f:
            current_face = []
            for line in f:
                line = line.strip().lower()
                if line.startswith("vertex"):
                    parts = line.split()
                    v = (
                        round(float(parts[1]), 6),
                        round(float(parts[2]), 6),
                        round(float(parts[3]), 6),
                    )
                    if v not in vertex_map:
                        vertex_map[v] = len(vertex_map)
                        vertices.append(v)
                    current_face.append(vertex_map[v])
                elif line.startswith("endloop"):
                    if len(current_face) == 3:
                        faces.append(current_face)
                    current_face = []
        return np.array(vertices, dtype=np.float32), np.array(
            faces, dtype=np.int32
        )
