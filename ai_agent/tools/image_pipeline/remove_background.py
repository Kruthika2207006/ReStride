import os


def remove_background(input_path, output_path=None):
    from rembg import remove


    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Image not found: {input_path}")

    if output_path is None:
        filename = os.path.basename(input_path)
        name, ext = os.path.splitext(filename)
        output_path = f"{name}_nobg.png"

    with open(input_path, "rb") as i:
        input_data = i.read()

    output_data = remove(input_data)

    with open(output_path, "wb") as o:
        o.write(output_data)

    return output_path


if __name__ == "__main__":

    image_path = input("Enter image path: ").strip().strip('"')

    output_file = remove_background(image_path)

    print(f"\nSaved: {output_file}")