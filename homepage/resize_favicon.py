"""
Resize image to favicon sizes
Run: pip install Pillow
Then: python resize_favicon.py
"""

from PIL import Image
import os

def create_favicon_sizes(input_image_path):
    """
    Create multiple favicon sizes from a single image
    """
    # Open the image
    img = Image.open(input_image_path)
    
    # Create output directory
    output_dir = 'static/images'
    os.makedirs(output_dir, exist_ok=True)
    
    # Different sizes needed for different devices
    sizes = {
        'favicon-16x16.png': 16,
        'favicon-32x32.png': 32,
        'favicon-48x48.png': 48,
        'favicon-64x64.png': 64,
        'apple-touch-icon.png': 180,
        'favicon.ico': 32,  # ICO format
    }
    
    print("Creating favicon files...")
    
    for filename, size in sizes.items():
        # Resize image
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Save in appropriate format
        if filename.endswith('.ico'):
            resized.save(os.path.join(output_dir, filename), 'ICO')
        else:
            # Convert to RGB if saving as PNG (remove alpha if needed)
            if resized.mode == 'RGBA':
                resized.save(os.path.join(output_dir, filename), 'PNG')
            else:
                resized = resized.convert('RGB')
                resized.save(os.path.join(output_dir, filename), 'PNG')
        
        print(f"✅ Created: {filename} ({size}x{size})")
    
    print(f"\n✅ All favicon files saved to: {output_dir}/")
    print("\nNext steps:")
    print("1. Add the favicon code to your base.html")
    print("2. Run 'python manage.py collectstatic'")
    print("3. Restart your server")

if __name__ == "__main__":
    # Replace 'your_image.png' with your actual image filename
    create_favicon_sizes('static/images/oncall_logo.png')