import os
import shutil


def remove_background(input_path, output_path=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Image not found: {input_path}")

    if output_path is None:
        filename = os.path.basename(input_path)
        name, ext = os.path.splitext(filename)
        output_path = f"{name}_nobg.png"

    try:
        from rembg import remove
        with open(input_path, "rb") as i:
            input_data = i.read()

        output_data = remove(input_data)

        with open(output_path, "wb") as o:
            o.write(output_data)
    except Exception as e:
        shutil.copy2(input_path, output_path)
        print(f"[remove_background] Warning: rembg failed or not installed. Falling back to copy: {e}")

    return output_path


if __name__ == "__main__":

    image_path = input("Enter image path: ").strip().strip('"')

    output_file = remove_background(image_path)

    print(f"\nSaved: {output_file}")