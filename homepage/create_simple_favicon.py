"""
Create a simple car favicon
Run: python create_simple_favicon.py
"""

from PIL import Image, ImageDraw
import os

# Create directories if they don't exist
os.makedirs('static/images', exist_ok=True)

# Create a 32x32 image
img = Image.new('RGB', (32, 32), color='#4CAF50')  # Green background
draw = ImageDraw.Draw(img)

# Draw a simple car shape
# Body
draw.rectangle([4, 16, 28, 24], fill='#FF5722', outline='black')
# Roof
draw.rectangle([10, 10, 22, 16], fill='#FF5722', outline='black')
# Windows
draw.rectangle([12, 11, 16, 15], fill='#87CEEB')
draw.rectangle([18, 11, 22, 15], fill='#87CEEB')
# Wheels
draw.ellipse([6, 22, 10, 26], fill='black')
draw.ellipse([22, 22, 26, 26], fill='black')

# Save as ICO and PNG
img.save('static/images/favicon.ico', format='ICO')
img.save('static/images/favicon.png', format='PNG')
img.save('static/images/favicon-32x32.png', format='PNG')

print("✅ Favicon created successfully!")
print("Files saved to:")
print("  - static/images/favicon.ico")
print("  - static/images/favicon.png")
print("  - static/images/favicon-32x32.png")