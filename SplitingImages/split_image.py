from PIL import Image
import os

# Create images directory if it doesn't exist
output_dir = "splitingImages/images/output"
os.makedirs(output_dir, exist_ok=True)

# Load image (replace "your_image.jpg" with your file)
print("Opening image...")
img = Image.open("splitingImages/images/sucket.jpg")  
width, height = img.size  
print(f"Image size: {width}x{height}")

# Split vertically into left and right halves
print("Splitting image...")
left = img.crop((0, 0, width // 2, height))  
right = img.crop((width // 2, 0, width, height))  

# Save the split images
print("Saving split images...")
left.save(os.path.join(output_dir, "left_half.jpg"))  
right.save(os.path.join(output_dir, "right_half.jpg"))  

print(f"Done! Images saved in: {output_dir}")