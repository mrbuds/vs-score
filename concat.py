import os
import sys
import re
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

def parse_folder_dates(folder_name):
    """Extract start and end dates from folder name in format 'sXwY dd-mm dd-mm'"""
    pattern = r'(\d{2})-(\d{2})\s+(\d{2})-(\d{2})$'
    match = re.search(pattern, folder_name)
    if not match:
        print(f"Warning: Could not parse dates from folder name '{folder_name}'. Using default headers.")
        return None
    
    try:
        start_day, start_month, end_day, end_month = map(int, match.groups())
        current_year = datetime.now().year
        
        start_date = datetime(current_year, start_month, start_day)
        end_date = datetime(current_year, end_month, end_day)
        
        # Verify date range (6 days from Monday to Saturday)
        if (end_date - start_date) != timedelta(days=5):
            print(f"Warning: Date range doesn't span 6 days ({start_date} to {end_date}). Using default headers.")
            return None
            
        return start_date
    except ValueError as e:
        print(f"Error parsing dates: {e}. Using default headers.")
        return None

def generate_headers(start_date):
    """Generate day headers with dates in French"""
    days_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
    headers = []
    current_date = start_date
    
    for day in days_fr:
        headers.append(f"{day} {current_date.strftime('%d/%m')}")
        current_date += timedelta(days=1)
    
    return headers

def concatenate_images(folder_path):
    folder_name = os.path.basename(os.path.normpath(folder_path))
    
    # Try to parse dates from folder name
    start_date = parse_folder_dates(folder_name)
    if start_date:
        headers = generate_headers(start_date)
    else:
        # Fallback to simple day names
        headers = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
    
    # Load original images
    original_images = []
    valid_days = []
    
    for i, day in enumerate(['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi']):
        img_path = os.path.join(folder_path, f"{day}.png")
        if os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                original_images.append(img)
                valid_days.append(headers[i])  # Keep corresponding header
            except Exception as e:
                print(f"Skipping {img_path}: {str(e)}")
    
    if not original_images:
        print("No valid images found in directory.")
        return
    
    # Calculate dimensions for final image
    max_height = max(img.height for img in original_images)
    total_width = sum(img.width for img in original_images)
    header_height = 50  # Height for the header row
    total_height = max_height + header_height
    
    # Create final image with transparent background
    result = Image.new('RGBA', (total_width, total_height), (255, 255, 255, 0))
    
    # Create header row with white background
    header_img = Image.new('RGBA', (total_width, header_height), (255, 255, 255, 255))
    header_draw = ImageDraw.Draw(header_img)
    
    # Try to load a nice font
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
        except:
            font = ImageFont.load_default()
    
    # Draw column headers
    x_offset = 0
    for img, header in zip(original_images, valid_days):
        text_width = header_draw.textlength(header, font=font)
        x = x_offset + (img.width - text_width) / 2
        y = (header_height - 30) / 2  # Vertically center in header
        
        # Draw text
        header_draw.text((x, y), header, font=font, fill=(0, 0, 0, 255))
        x_offset += img.width
    
    # Paste header at top of final image
    result.paste(header_img, (0, 0))
    
    # Concatenate images horizontally below header
    x_offset = 0
    for img in original_images:
        # Place image below header (top-aligned)
        result.paste(img, (x_offset, header_height))
        x_offset += img.width
    
    # Save result using folder name
    output_path = os.path.join(folder_path, f"{folder_name}.png")
    result.save(output_path)
    print(f"Saved concatenated image to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python concatenate.py <folder_path>")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    if not os.path.isdir(folder_path):
        print(f"Error: {folder_path} is not a valid directory")
        sys.exit(1)
    
    concatenate_images(folder_path)