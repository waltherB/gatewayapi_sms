#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to generate a new banner image for the GatewayAPI SMS module
"""

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: This script requires the Pillow library.")
    print("Please install it with: pip install Pillow")
    exit(1)

# Settings
WIDTH = 560
HEIGHT = 280
BACKGROUND_COLOR = (255, 255, 255)  # White
PRIMARY_COLOR = (0, 210, 210)  # Teal (similar to GatewayAPI branding)
SECONDARY_COLOR = (59, 59, 59)  # Dark gray for text

def create_banner():
    # Create a new image with white background
    img = Image.new('RGB', (WIDTH, HEIGHT), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Draw a teal bar at the top
    draw.rectangle([(0, 0), (WIDTH, 60)], fill=PRIMARY_COLOR)
    
    # Try to load a font, or use default if unavailable
    try:
        # Try to use a nice font if available
        title_font = ImageFont.truetype("Arial.ttf", 38)
        subtitle_font = ImageFont.truetype("Arial.ttf", 22)
    except IOError:
        # Fall back to default font
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
    
    # Add title text
    title = "GatewayAPI SMS Connector"
    draw.text((30, 95), title, font=title_font, fill=SECONDARY_COLOR)
    
    # Add subtitle
    subtitle = "Send SMS directly from Odoo using GatewayAPI"
    draw.text((30, 150), subtitle, font=subtitle_font, fill=SECONDARY_COLOR)
    
    # Add features
    features = [
        "✓ Simple Integration",
        "✓ Credit Balance Monitoring",
        "✓ Secure API Token Management",
        "✓ Admin Notifications"
    ]
    
    y_position = 190
    for feature in features:
        draw.text((30, y_position), feature, font=subtitle_font, fill=SECONDARY_COLOR)
        y_position += 25
    
    # Save the banner
    output_path = "../static/description/banner.png"
    img.save(output_path)
    print(f"Banner created and saved to {output_path}")
    
if __name__ == "__main__":
    import os
    # Get the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Change to the script directory to make relative paths work
    os.chdir(script_dir)
    
    print("Generating new banner image...")
    create_banner() 