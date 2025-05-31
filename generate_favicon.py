from PIL import Image, ImageDraw
import os


def create_favicon(size):
    # Create a new image with a white background
    image = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)

    # Draw a simple fork and knife icon
    # Fork
    fork_color = (44, 62, 80)  # Primary color
    fork_width = size // 4
    fork_height = size * 3 // 4
    fork_x = size // 2 - fork_width
    fork_y = size // 8

    # Draw fork handle
    draw.rectangle(
        [fork_x, fork_y, fork_x + fork_width, fork_y + fork_height], fill=fork_color
    )

    # Draw fork tines
    tine_width = fork_width // 3
    tine_spacing = tine_width
    for i in range(3):
        tine_x = fork_x + (i * (tine_width + tine_spacing))
        draw.rectangle(
            [tine_x, fork_y, tine_x + tine_width, fork_y + fork_height // 3],
            fill=fork_color,
        )

    # Knife
    knife_width = fork_width
    knife_height = fork_height
    knife_x = size // 2
    knife_y = fork_y

    # Draw knife handle
    draw.rectangle(
        [knife_x, knife_y, knife_x + knife_width, knife_y + knife_height],
        fill=fork_color,
    )

    # Draw knife blade
    blade_width = knife_width
    blade_height = knife_height // 2
    draw.rectangle(
        [
            knife_x,
            knife_y + knife_height // 2,
            knife_x + blade_width,
            knife_y + knife_height,
        ],
        fill=fork_color,
    )

    return image


def main():
    # Create static directory if it doesn't exist
    os.makedirs("static", exist_ok=True)

    # Generate different sizes
    sizes = {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "apple-touch-icon.png": 180,
        "android-chrome-192x192.png": 192,
        "android-chrome-512x512.png": 512,
    }

    for filename, size in sizes.items():
        image = create_favicon(size)
        image.save(os.path.join("static", filename))
        print(f"Generated {filename}")


if __name__ == "__main__":
    main()
