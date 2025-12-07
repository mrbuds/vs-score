#!/usr/bin/env python3
"""
Traitement vidéo vers panorama
Version corrigée - algorithme original restauré
"""

import cv2
import numpy as np
import os
import sys
import time


def is_duplicate_frame(frame1, frame2, threshold=5):
    """
    Vérifie si deux frames sont des doublons.
    
    Args:
        frame1, frame2: Frames à comparer
        threshold: Seuil de différence en pourcentage
    
    Returns:
        True si les frames sont considérées comme doublons
    """
    if frame1 is None or frame2 is None:
        return False
    if frame1.shape != frame2.shape:
        return False
    
    # Convertir en niveaux de gris
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # Calculer la différence absolue
    diff = cv2.absdiff(gray1, gray2)
    
    # Seuiller et compter les pixels modifiés
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    changed_pixels = np.count_nonzero(thresh)
    total_pixels = gray1.shape[0] * gray1.shape[1]
    change_percent = (changed_pixels / total_pixels) * 100
    
    return change_percent < threshold


def main():
    if len(sys.argv) < 2:
        print("Usage: python panorama.py <input_video>")
        sys.exit(1)
    
    input_video = sys.argv[1]
    output_file = os.path.splitext(input_video)[0] + '.png'
    
    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        print("Error: Could not open video file")
        sys.exit(1)
    
    # Propriétés vidéo
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"Processing: {input_video}")
    print(f"Resolution: {frame_width}px wide, Frames: {total_frames}, FPS: {fps:.1f}")
    
    # Lire la première frame
    ret, prev = cap.read()
    if not ret:
        print("Error: Failed to read first frame")
        sys.exit(1)
    
    # Initialiser le panorama
    panorama = prev.copy()
    
    # Paramètres (depuis environnement ou valeurs par défaut)
    min_scroll = int(os.environ.get('MIN_SCROLL', 5))
    template_height = int(os.environ.get('TEMPLATE_HEIGHT', 100))
    min_match_quality = float(os.environ.get('QUALITY_THRESHOLD', 0.8))
    
    frame_count = 1
    last_frame = prev.copy()
    duplicates_skipped = 0
    
    print(f"Parameters: template_height={template_height}, quality={min_match_quality}")
    print("Processing frames...")
    start_time = time.time()
    
    while True:
        ret, curr = cap.read()
        if not ret:
            break
        
        # Maintenir une largeur constante
        if curr.shape[1] != frame_width:
            ratio = frame_width / curr.shape[1]
            new_height = int(curr.shape[0] * ratio)
            curr = cv2.resize(curr, (frame_width, new_height))
        
        # 1. Vérifier les doublons
        if is_duplicate_frame(last_frame, curr):
            duplicates_skipped += 1
            print(f"Frame {frame_count}: Duplicate skipped ({duplicates_skipped} total)")
            frame_count += 1
            last_frame = curr.copy()
            continue
        
        # Convertir en niveaux de gris
        curr_gray = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY)
        
        # 2. Template matching - utiliser le bas du panorama comme template
        if panorama.shape[0] < template_height:
            template = panorama
        else:
            template = panorama[-template_height:, :]
        
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        # Chercher le template dans toute la frame courante (algorithme original)
        result = cv2.matchTemplate(curr_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        match_y = max_loc[1]
        
        # Calculer le scroll
        scroll_amount = match_y
        
        # 3. Ajouter le nouveau contenu
        content_added = 0
        if max_val > min_match_quality:
            # Contenu sous la région matchée
            content_start = match_y + template_gray.shape[0]
            if content_start < curr.shape[0]:
                new_content = curr[content_start:, :]
                if new_content.shape[0] > min_scroll:
                    panorama = np.vstack((panorama, new_content))
                    content_added = new_content.shape[0]
        
        # Status
        status = f"Match: {max_val:.2f}, Scroll: {scroll_amount}px"
        if content_added:
            status += f", Added: {content_added}px"
        else:
            status += ", No new content"
        print(f"Frame {frame_count}: {status}")
        
        # Mise à jour
        last_frame = curr.copy()
        frame_count += 1
        
        # Progression toutes les 10 frames
        if frame_count % 10 == 0 or frame_count == total_frames:
            elapsed = time.time() - start_time
            fps_processed = frame_count / elapsed if elapsed > 0 else 0
            print(f"Progress: {frame_count}/{total_frames} frames | "
                  f"Elapsed: {elapsed:.1f}s | "
                  f"FPS: {fps_processed:.1f} | "
                  f"Height: {panorama.shape[0]}px")
    
    cap.release()
    
    if panorama.size == 0:
        print("Error: Empty panorama generated")
        sys.exit(1)
    
    # Sauvegarder
    cv2.imwrite(output_file, panorama)
    print(f"\nSaved panorama to {output_file}")
    print(f"Final dimensions: {panorama.shape[1]}x{panorama.shape[0]} pixels")
    print(f"Duplicates skipped: {duplicates_skipped}")
    print(f"Processing time: {time.time() - start_time:.1f} seconds")


if __name__ == "__main__":
    main()