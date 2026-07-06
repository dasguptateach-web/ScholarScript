import os
from PIL import Image, ImageDraw

ico_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
os.makedirs(os.path.dirname(ico_path), exist_ok=True)

img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

draw.ellipse([2, 2, 30, 30], fill=(30, 30, 30, 255))
draw.rectangle([10, 6, 24, 12], fill=(76, 175, 80, 255))
draw.rectangle([10, 14, 24, 18], fill=(76, 175, 80, 255))
draw.rectangle([10, 20, 24, 26], fill=(76, 175, 80, 255))

img.save(ico_path, format="ICO", sizes=[(32, 32)])
print(f"Icon created: {ico_path}")
