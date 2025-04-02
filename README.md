# Image Splitting Tool

A Python tool that can split images in two ways:

1. Simple vertical split (left and right halves)
2. Smart detection and splitting of square/rectangular regions in an image

## Features

- Split images vertically into left and right halves
- Detect and extract square/rectangular regions from images
- Visualize detected regions with bounding boxes
- Save individual extracted images

## Requirements

- Python 3.x
- OpenCV (cv2)
- Pillow (PIL)
- NumPy

## Installation

```bash
pip install opencv-python pillow numpy
```

## Usage

1. Place your image in the `splitingImages/images/` directory
2. Run either script:
   - `split_image.py` for simple vertical split
   - `split_square_images.py` for detecting and splitting square regions

## Output

- Split images are saved in `splitingImages/images/output/`
- For square detection, a visualization file `detected_boxes.jpg` is also created
