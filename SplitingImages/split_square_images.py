import cv2
import numpy as np
import os
from PIL import Image

def detect_and_split_images(image_path):
    # Create output directory
    output_dir = "splitingImages/images/output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the image
    print("Opening image...")
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not open image at {image_path}")
        return
    
    # Convert to HSV color space for better color detection
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Define blue color range in HSV
    lower_blue = np.array([100, 100, 100])
    upper_blue = np.array([130, 255, 255])
    
    # Create mask for blue color
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    
    # Find contours of blue regions
    contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter and process contours
    print("Detecting images with blue borders...")
    for i, contour in enumerate(contours):
        # Get the bounding rectangle
        x, y, w, h = cv2.boundingRect(contour)
        
        # Filter out very small contours
        if w < 50 or h < 50:
            continue
            
        # Calculate aspect ratio
        aspect_ratio = float(w)/h
        
        # Filter for roughly square shapes (aspect ratio between 0.8 and 1.2)
        if 0.8 <= aspect_ratio <= 1.2:
            # Add padding to include the full image
            padding = 5
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(img.shape[1] - x, w + 2*padding)
            h = min(img.shape[0] - y, h + 2*padding)
            
            # Extract the region
            roi = img[y:y+h, x:x+w]
            
            # Save the image
            output_path = os.path.join(output_dir, f"image_{i+1}.jpg")
            cv2.imwrite(output_path, roi)
            print(f"Saved image {i+1} to {output_path}")
            
            # Draw rectangle around detected image (for visualization)
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
    
    # Save the visualization
    cv2.imwrite(os.path.join(output_dir, "detected_boxes.jpg"), img)
    print(f"\nDone! Check the output directory: {output_dir}")
    print("detected_boxes.jpg shows the detected regions with green boxes")

if __name__ == "__main__":
    image_path = "splitingImages/images/sucket.jpg"
    detect_and_split_images(image_path)