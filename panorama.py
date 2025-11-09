import cv2
import numpy as np
import os
import sys
import time

def is_duplicate_frame(frame1, frame2, threshold=5):
    """Check if two frames are duplicates using pixel difference"""
    if frame1 is None or frame2 is None:
        return False
    if frame1.shape != frame2.shape:
        return False
        
    # Convert to grayscale
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # Compute absolute difference
    diff = cv2.absdiff(gray1, gray2)
    
    # Calculate percentage of changed pixels
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    changed_pixels = np.count_nonzero(thresh)
    total_pixels = gray1.shape[0] * gray1.shape[1]
    change_percent = (changed_pixels / total_pixels) * 100
    
    # Return True if change is below threshold
    return change_percent < threshold

def main():
    if len(sys.argv) < 2:
        print("Usage: python video_to_panorama.py <input_video>")
        sys.exit(1)
    
    input_video = sys.argv[1]
    output_file = os.path.splitext(input_video)[0] + '.png'
    
    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        print("Error: Could not open video file")
        sys.exit(1)
    
    # Get video properties
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"Processing: {input_video}")
    print(f"Resolution: {frame_width}px wide, Frames: {total_frames}, FPS: {fps:.1f}")
    
    # Read first frame
    ret, prev = cap.read()
    if not ret:
        print("Error: Failed to read first frame")
        sys.exit(1)
    
    # Initialize panorama with first frame
    panorama = prev.copy()
    prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
    
    # Parameters
    min_scroll = 5  # Minimum pixels of movement to consider
    template_height = 100  # Height of the template for matching
    min_match_quality = 0.8  # Minimum match quality to accept
    
    frame_count = 1
    last_frame = prev.copy()
    duplicates_skipped = 0
    
    print("Processing frames...")
    start_time = time.time()
    
    while True:
        ret, curr = cap.read()
        if not ret:
            break
        
        # Maintain consistent width
        if curr.shape[1] != frame_width:
            ratio = frame_width / curr.shape[1]
            new_height = int(curr.shape[0] * ratio)
            curr = cv2.resize(curr, (frame_width, new_height))
        
        # 1. Check for duplicate frames - only skip if truly identical
        if is_duplicate_frame(last_frame, curr):
            duplicates_skipped += 1
            print(f"Frame {frame_count}: Duplicate skipped ({duplicates_skipped} total)")
            frame_count += 1
            last_frame = curr.copy()  # Update last frame reference
            continue
        
        # Process the frame
        curr_gray = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY)
        
        # 2. Use template matching to find scroll offset
        # Create template from bottom of panorama
        if panorama.shape[0] < template_height:
            template = panorama
        else:
            template = panorama[-template_height:, :]
        
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        # Match template in current frame
        result = cv2.matchTemplate(curr_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        match_y = max_loc[1]
        
        # Calculate scroll amount based on match position
        scroll_amount = match_y
        
        # 3. Add new content based on scroll position
        content_added = 0
        if max_val > min_match_quality:
            # Get content below the matched region
            content_start = match_y + template_gray.shape[0]
            if content_start < curr.shape[0]:
                new_content = curr[content_start:, :]
                if new_content.shape[0] > min_scroll:
                    panorama = np.vstack((panorama, new_content))
                    content_added = new_content.shape[0]
        
        # Print status
        status = f"Match: {max_val:.2f}, Scroll: {scroll_amount}px"
        if content_added:
            status += f", Added: {content_added}px"
        else:
            status += ", No new content"
        print(f"Frame {frame_count}: {status}")
        
        # Update frame references
        last_frame = curr.copy()
        frame_count += 1
        
        # Show progress every 10 frames
        if frame_count % 10 == 0 or frame_count == total_frames:
            elapsed = time.time() - start_time
            fps_processed = frame_count / elapsed
            print(f"Progress: {frame_count}/{total_frames} frames | "
                  f"Elapsed: {elapsed:.1f}s | "
                  f"FPS: {fps_processed:.1f} | "
                  f"Height: {panorama.shape[0]}px")
    
    cap.release()
    
    if panorama.size == 0:
        print("Error: Empty panorama generated")
        sys.exit(1)
    
    # Save final panorama
    cv2.imwrite(output_file, panorama)
    print(f"Saved panorama to {output_file}")
    print(f"Final dimensions: {panorama.shape[1]}x{panorama.shape[0]} pixels")
    print(f"Duplicates skipped: {duplicates_skipped}")
    print(f"Processing time: {time.time() - start_time:.1f} seconds")

if __name__ == "__main__":
    main()