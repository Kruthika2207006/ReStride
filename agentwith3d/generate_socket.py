"""CLI driver for the procedural 3D prosthetic socket generator.

Loads a recommendation JSON, generates the socket mesh, exports the STL, and renders a PNG screenshot.
"""

import os
import json
import argparse
import numpy as np

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False

from tools.socket_generator import generate_socket
from tools.mesh_loader import MeshLoader


def main():
    parser = argparse.ArgumentParser(description="Procedural 3D Prosthetic Socket Generator")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to the recommendation JSON file. If omitted, uses default parameters.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="generated/socket_output.stl",
        help="Output path for the generated STL file.",
    )
    parser.add_argument(
        "--render",
        type=str,
        default="generated/socket_render.png",
        help="Output path for the rendered PNG image.",
    )
    args = parser.parse_args()

    # 1. Load recommendation parameters
    if args.config and os.path.exists(args.config):
        print(f"Loading recommendation config from: {args.config}")
        with open(args.config, "r") as f:
            recommendation = json.load(f)
    else:
        print("No config file provided or not found. Using default recommendation parameters...")
        recommendation = {
            "residual_limb_shape": "Conical",
            "socket_type": "TSB",
            "suspension": "Suction",
            "material": "Carbon Fiber Composite",
            "estimated_length_cm": 15,
            "average_width_ratio": 2.173,
            "wall_thickness_mm": 4,
            "radial_expansion_mm": 1,
            "distal_clearance_mm": 4,
        }

    print("Recommendation JSON Configuration:")
    print(json.dumps(recommendation, indent=4))

    # 2. Make sure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    render_dir = os.path.dirname(args.render)
    if render_dir:
        os.makedirs(render_dir, exist_ok=True)

    # 3. Generate the 3D socket mesh
    print("\nGenerating 3D prosthetic socket model procedurally...")
    try:
        mesh = generate_socket(recommendation)
        print("Geometry generation complete!")
    except Exception as e:
        print(f"Error generating socket geometry: {str(e)}")
        return

    # 4. Save to STL
    print(f"\nExporting mesh to: {args.output}")
    try:
        # Open3D write_triangle_mesh exports to STL, OBJ, PLY, etc.
        o3d.io.write_triangle_mesh(args.output, mesh)
        print("STL export complete!")
    except Exception as e:
        print(f"Error exporting STL: {str(e)}")
        return

    # 5. Load and validate output mesh using our validation tools
    print("\nValidating and checking mesh integrity using ReStride validation tools...")
    try:
        loaded_limb_mesh = MeshLoader.load_stl(args.output)
        repaired_mesh, is_watertight, mesh_status, errors = MeshLoader.validate_and_repair(loaded_limb_mesh)
        print(f"Mesh Status: {mesh_status}")
        print(f"Is Watertight: {is_watertight}")
        print(f"Number of Vertices: {repaired_mesh.num_vertices}")
        print(f"Number of Triangles: {repaired_mesh.num_triangles}")
        if errors:
            print("Validation Errors/Warnings:")
            for err in errors:
                print(f" - {err}")
        else:
            print("Mesh validation PASSED: Watertight, manifold, and printable!")
    except Exception as e:
        print(f"Validation step encountered an error: {str(e)}")

    # 6. Capture screenshot render using Open3D
    print(f"\nRendering 3D model to image: {args.render}")
    try:
        vis = o3d.visualization.Visualizer()
        # Set visible=False for headless screenshot capturing (offscreen)
        # Note: on some Windows systems with older OpenGL drivers, offscreen capturing
        # might need a visible window. We start with visible=False.
        vis.create_window(window_name="ReStride Prosthetic Socket", width=1024, height=1024, visible=False)

        # Apply a premium, high-contrast visual paint to the socket mesh (Steel Blue)
        mesh.paint_uniform_color([0.2, 0.45, 0.7])

        vis.add_geometry(mesh)

        # Render configurations
        opt = vis.get_render_option()
        opt.background_color = np.array([0.95, 0.95, 0.95])  # Off-white background
        opt.mesh_show_back_face = True  # Ensure internal cavity is rendered properly
        opt.show_coordinate_frame = False

        # Adjust camera viewpoint to see inside the hollow socket from a 3/4 angle
        ctr = vis.get_view_control()
        # Rotate camera to look down into the open proximal end from a premium angle
        ctr.rotate(180.0, -160.0)
        ctr.set_zoom(0.85)

        vis.poll_events()
        vis.update_renderer()

        # Capture and save screenshot image
        vis.capture_screen_image(args.render)
        vis.destroy_window()
        print("Render screenshot complete!")
    except Exception as e:
        print(f"Error capturing render screenshot: {str(e)}")


if __name__ == "__main__":
    main()
