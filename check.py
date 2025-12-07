#!/usr/bin/env python3
"""
Test direct du traitement parallèle
Lance plusieurs instances de panorama.py en parallèle
"""

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from pathlib import Path

from config import config


def process_video(video_file, script='panorama.py'):
    """Traite une vidéo"""
    print(f"[{time.strftime('%H:%M:%S')}] Démarrage: {video_file}")
    
    try:
        cmd = [sys.executable, script, video_file]
        start_time = time.time()
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Lire la sortie en temps réel
        while True:
            line = process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line and ("Progress:" in line or "Frame" in line):
                print(f"  [{Path(video_file).stem}] {line}")
        
        process.wait()
        elapsed = time.time() - start_time
        
        if process.returncode == 0:
            print(f"[{time.strftime('%H:%M:%S')}] ✓ Terminé: {video_file} ({elapsed:.1f}s)")
            return True, elapsed
        else:
            stderr = process.stderr.read()
            print(f"[{time.strftime('%H:%M:%S')}] ✗ Erreur: {video_file}")
            if stderr:
                print(f"  Stderr: {stderr[:200]}")
            return False, elapsed
    
    except FileNotFoundError as e:
        print(f"[{time.strftime('%H:%M:%S')}] ✗ Fichier non trouvé: {e.filename}")
        return False, 0
    
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ✗ Exception pour {video_file}: {type(e).__name__}: {e}")
        return False, 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python check.py <video1.mp4> <video2.mp4> ...")
        print("   ou: python check.py --test  (pour utiliser test_panorama.py)")
        sys.exit(1)
    
    # Vérifier si on veut utiliser le script de test
    if sys.argv[1] == '--test':
        script = 'test_panorama.py'
        video_files = sys.argv[2:] if len(sys.argv) > 2 else ['test1.mp4', 'test2.mp4', 'test3.mp4']
    else:
        script = 'panorama.py'
        video_files = sys.argv[1:]
    
    if not video_files:
        print("Aucun fichier vidéo spécifié")
        sys.exit(1)
    
    max_workers = min(config.max_workers, len(video_files))
    
    print("=" * 50)
    print("=== Test de traitement parallèle ===")
    print(f"Script: {script}")
    print(f"Fichiers: {', '.join(video_files)}")
    print(f"Nombre de workers: {max_workers}")
    print("=" * 50)
    
    # Traitement séquentiel (pour comparaison) - seulement si plusieurs fichiers
    if len(video_files) >= 2:
        print("\n📋 TRAITEMENT SÉQUENTIEL (pour comparaison, 2 fichiers):")
        start_seq = time.time()
        seq_times = []
        for video in video_files[:2]:
            success, elapsed = process_video(video, script)
            if success:
                seq_times.append(elapsed)
        time_seq = time.time() - start_seq
        print(f"⏱️ Temps total séquentiel: {time_seq:.1f}s\n")
    else:
        time_seq = 0
    
    # Traitement parallèle
    print("🚀 TRAITEMENT PARALLÈLE:")
    start_par = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_video, video, script): video for video in video_files}
        
        results = []
        times = []
        for future in as_completed(futures):
            video = futures[future]
            try:
                success, elapsed = future.result()
                results.append((video, success))
                if success:
                    times.append(elapsed)
            except Exception as e:
                print(f"Exception pour {video}: {type(e).__name__}: {e}")
                results.append((video, False))
    
    time_par = time.time() - start_par
    
    # Résumé
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ:")
    print(f"⏱️ Temps parallèle: {time_par:.1f}s")
    
    if time_seq > 0:
        print(f"⏱️ Temps séquentiel (2 fichiers): {time_seq:.1f}s")
        if time_par > 0:
            speedup = time_seq / time_par
            print(f"🎯 Speedup: {speedup:.2f}x")
    
    if times:
        avg_time = sum(times) / len(times)
        print(f"⏱️ Temps moyen par vidéo: {avg_time:.1f}s")
    
    successful = sum(1 for _, success in results if success)
    print(f"✅ Succès: {successful}/{len(results)}")
    
    if len(video_files) > 1:
        print("\n💡 Si les messages 'Démarrage' apparaissent rapidement")
        print("   les uns après les autres, le parallélisme fonctionne!")


if __name__ == "__main__":
    main()
