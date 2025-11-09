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

def process_video(video_file, script='panorama.py'):
    """Traite une vidéo"""
    print(f"[{time.strftime('%H:%M:%S')}] Démarrage: {video_file}")
    
    try:
        # Lancer le script
        cmd = [sys.executable, script, video_file]
        start_time = time.time()
        
        # Exécuter et capturer la sortie
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
            return True
        else:
            print(f"[{time.strftime('%H:%M:%S')}] ✗ Erreur: {video_file}")
            return False
            
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ✗ Exception pour {video_file}: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_parallel.py <video1.mp4> <video2.mp4> ...")
        print("   ou: python test_parallel.py --test  (pour utiliser test_panorama.py)")
        sys.exit(1)
    
    # Vérifier si on veut utiliser le script de test
    if sys.argv[1] == '--test':
        script = 'test_panorama.py'  # ou 'check.py'
        video_files = sys.argv[2:] if len(sys.argv) > 2 else ['test1.mp4', 'test2.mp4', 'test3.mp4']
    else:
        script = 'panorama.py'
        video_files = sys.argv[1:]
    
    if not video_files:
        print("Aucun fichier vidéo spécifié")
        sys.exit(1)
    
    print(f"=== Test de traitement parallèle ===")
    print(f"Script: {script}")
    print(f"Fichiers: {', '.join(video_files)}")
    print(f"Nombre de workers: {min(3, len(video_files))}")
    print("=" * 40)
    
    # Traitement séquentiel (pour comparaison)
    print("\n📋 TRAITEMENT SÉQUENTIEL (pour comparaison):")
    start_seq = time.time()
    for video in video_files[:2]:  # Juste 2 pour la démo
        process_video(video, script)
    time_seq = time.time() - start_seq
    print(f"⏱️ Temps total séquentiel: {time_seq:.1f}s\n")
    
    # Traitement parallèle
    print("🚀 TRAITEMENT PARALLÈLE:")
    start_par = time.time()
    
    with ThreadPoolExecutor(max_workers=min(3, len(video_files))) as executor:
        # Soumettre tous les jobs
        futures = {executor.submit(process_video, video, script): video for video in video_files}
        
        # Attendre les résultats
        results = []
        for future in as_completed(futures):
            video = futures[future]
            try:
                success = future.result()
                results.append((video, success))
            except Exception as e:
                print(f"Exception pour {video}: {e}")
                results.append((video, False))
    
    time_par = time.time() - start_par
    
    # Résumé
    print("\n" + "=" * 40)
    print("📊 RÉSUMÉ:")
    print(f"⏱️ Temps parallèle: {time_par:.1f}s")
    print(f"⏱️ Temps séquentiel (2 fichiers): {time_seq:.1f}s")
    if time_seq > 0:
        print(f"🎯 Gain de performance: {(time_seq/time_par - 1)*100:.0f}%")
    
    successful = sum(1 for _, success in results if success)
    print(f"✅ Succès: {successful}/{len(results)}")
    
    # Montrer clairement si le parallélisme fonctionne
    if len(video_files) > 1:
        print("\n💡 Si vous voyez les messages de 'Démarrage' apparaître")
        print("   rapidement les uns après les autres, le parallélisme fonctionne!")
        print("   Sinon, ils apparaissent un par un après chaque 'Terminé'.")

if __name__ == "__main__":
    main()