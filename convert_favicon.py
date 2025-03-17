import os
import cairosvg

# Create PNG versions of favicon in different sizes
sizes = [16, 32, 64, 128, 192, 512]

input_file = os.path.join('static', 'images', 'favicon.svg')
for size in sizes:
    output_file = os.path.join('static', 'images', f'favicon-{size}.png')
    cairosvg.svg2png(url=input_file, write_to=output_file, output_width=size, output_height=size)

# Create main favicon.png
cairosvg.svg2png(url=input_file, write_to=os.path.join('static', 'images', 'favicon.png'), output_width=64, output_height=64)

print("Favicon PNG files generated successfully!")