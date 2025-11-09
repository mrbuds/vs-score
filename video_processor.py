#!/usr/bin/env python3
"""
Module 1 : Traitement parallèle des vidéos
"""

import subprocess
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import shutil
import queue
import os

class VideoProcessor:
    def __init__(self, parent):
        self.parent = parent
        self.processing_active = False
        
    def process_selected_videos(self):
        """Traite les vidéos sélectionnées en parallèle"""
        selection = self.parent.video_tree.selection()
        if not selection:
            from tkinter import messagebox
            messagebox.showwarning("Sélection", "Veuillez sélectionner au moins une vidéo")
            return
            
        days = []
        for item in selection:
            values = self.parent.video_tree.item(item)['values']
            days.append(values[0])
            
        self.start_parallel_processing(days)
        
    def process_all_videos(self):
        """Traite toutes les vidéos en parallèle"""
        if not self.parent.video_files:
            from tkinter import messagebox
            messagebox.showwarning("Aucune vidéo", "Veuillez d'abord charger des vidéos")
            return
            
        self.start_parallel_processing(list(self.parent.video_files.keys()))
    
    def start_parallel_processing(self, days):
        """Lance le traitement parallèle des vidéos"""
        if self.processing_active:
            from tkinter import messagebox
            messagebox.showwarning("Traitement en cours", "Un traitement est déjà en cours")
            return
            
        self.processing_active = True
        thread = threading.Thread(target=self.run_parallel_processing, args=(days,))
        thread.daemon = True
        thread.start()
    
    def run_parallel_processing(self, days):
        """Exécute le traitement en parallèle dans un thread"""
        max_workers = self.parent.max_workers.get()
        
        self.parent.log("="*50)
        self.parent.log(f"🚀 DÉMARRAGE DU TRAITEMENT PARALLÈLE")
        self.parent.log(f"📊 {len(days)} vidéo(s) à traiter")
        self.parent.log(f"⚡ {max_workers} worker(s) parallèle(s)")
        self.parent.log("="*50)
        
        for day in days:
            self.parent.update_queue.put(('status', day, '⏳ En attente', ''))
        
        completed = 0
        failed = 0
        start_time = time.time()
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for day in days:
                    if day in self.parent.video_files:
                        future = executor.submit(self.process_single_video, day)
                        futures[future] = day
                        self.parent.log(f"📤 Job soumis: {day}")
                        self.parent.update_queue.put(('status', day, '🔄 Démarrage...', '0%'))
                
                for future in as_completed(futures):
                    day = futures[future]
                    try:
                        success = future.result(timeout=300)
                        completed += 1
                        
                        if success:
                            self.parent.log(f"✅ {day}: Terminé avec succès")
                            self.parent.update_queue.put(('status', day, '✅ Terminé', '100%'))
                        else:
                            failed += 1
                            self.parent.log(f"❌ {day}: Échec")
                            self.parent.update_queue.put(('status', day, '❌ Erreur', ''))
                            
                    except Exception as e:
                        failed += 1
                        completed += 1
                        self.parent.log(f"❌ {day}: Exception - {str(e)}")
                        self.parent.update_queue.put(('status', day, '❌ Exception', ''))
                    
                    self.parent.update_status(f"Progression: {completed}/{len(days)}")
                    
        finally:
            elapsed = time.time() - start_time
            self.parent.log("="*50)
            self.parent.log(f"🏁 TRAITEMENT TERMINÉ")
            self.parent.log(f"⏱️ Temps total: {elapsed:.1f}s")
            self.parent.log(f"📊 Succès: {completed - failed}/{completed}")
            self.parent.log("="*50)
            
            self.processing_active = False
            self.parent.update_status("Prêt")
            self.parent.root.after(500, self.final_status_update, days)
            
            from tkinter import messagebox
            if failed == 0:
                messagebox.showinfo("Succès", f"Traitement terminé!\n{completed} vidéos en {elapsed:.1f}s")
            else:
                messagebox.showwarning("Terminé avec erreurs", f"{completed-failed} succès, {failed} erreurs")
    
    def process_single_video(self, day):
        """Traite une seule vidéo"""
        video_path = self.parent.video_files[day]
        output_path = video_path.parent / f"{day}.png"
        
        self.parent.update_queue.put(('log', f"🎬 Début: {day} [Worker-{threading.get_ident() % 100}]"))
        self.parent.update_queue.put(('status', day, '🔄 En cours...', '0%'))
        
        success = False
        try:
            script_path = Path('panorama.py')
            if not script_path.exists():
                script_path = Path(__file__).parent / 'panorama.py'
                if not script_path.exists():
                    self.parent.update_queue.put(('status', day, '❌ Script manquant', ''))
                    return False
            
            cmd = [os.sys.executable, str(script_path), str(video_path)]
            env = os.environ.copy()
            env['TEMPLATE_HEIGHT'] = str(int(self.parent.template_height.get()))
            env['QUALITY_THRESHOLD'] = str(self.parent.quality_threshold.get())
            
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=env, bufsize=1, universal_newlines=True
            )
            
            last_update = time.time()
            last_percent = 0
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                    
                if line:
                    current_time = time.time()
                    if current_time - last_update > 0.5:
                        line = line.strip()
                        
                        if "Frame" in line or "Progress:" in line:
                            try:
                                if "/" in line:
                                    parts = line.split("/")
                                    current_str = ''.join(filter(str.isdigit, parts[0].split()[-1]))
                                    total_str = ''.join(filter(str.isdigit, parts[1].split()[0]))
                                    
                                    if current_str and total_str:
                                        current = int(current_str)
                                        total = int(total_str)
                                        percent = int((current / total) * 100)
                                        
                                        if percent != last_percent:
                                            self.parent.update_queue.put(('status', day, '🔄 En cours...', f'{percent}%'))
                                            last_percent = percent
                                            last_update = current_time
                            except:
                                pass
            
            stdout, stderr = process.communicate(timeout=300)
            
            if process.returncode == 0:
                expected = video_path.with_suffix('.png')
                if expected.exists():
                    if expected != output_path:
                        shutil.move(str(expected), str(output_path))
                    
                    self.parent.panorama_files[day] = output_path
                    success = True
            
            if not success and stderr:
                self.parent.update_queue.put(('error', day, stderr[:200]))
            
        except subprocess.TimeoutExpired:
            self.parent.update_queue.put(('error', day, "Timeout après 5 minutes"))
            process.kill()
        except Exception as e:
            self.parent.update_queue.put(('error', day, str(e)[:100]))
        
        if success:
            for i in range(3):
                self.parent.update_queue.put(('status', day, '✅ Terminé', '100%'))
                time.sleep(0.1)
            self.parent.update_queue.put(('final', day, True))
        else:
            for i in range(3):
                self.parent.update_queue.put(('status', day, '❌ Échec', ''))
                time.sleep(0.1)
            self.parent.update_queue.put(('final', day, False))
        
        return success
    
    def final_status_update(self, days):
        """Mise à jour finale des statuts"""
        self.parent.log("🔄 Vérification finale des statuts...")
        corrections_made = 0
        
        for day in days:
            expected_file = None
            if day in self.parent.video_files:
                video_path = self.parent.video_files[day]
                expected_file = video_path.parent / f"{day}.png"
            
            if expected_file and expected_file.exists():
                correct_status = '✅ Terminé'
                correct_progress = '100%'
            elif day in self.parent.panorama_files and self.parent.panorama_files[day].exists():
                correct_status = '✅ Terminé'
                correct_progress = '100%'
            else:
                if day in self.parent.final_statuses:
                    correct_status, correct_progress = self.parent.final_statuses[day]
                else:
                    correct_status = '❌ Fichier non trouvé'
                    correct_progress = ''
            
            for item in self.parent.video_tree.get_children():
                values = list(self.parent.video_tree.item(item)['values'])
                if values[0] == day:
                    current_status = values[2] if len(values) > 2 else ''
                    current_progress = values[3] if len(values) > 3 else ''
                    
                    if current_status != correct_status or current_progress != correct_progress:
                        self.parent.video_tree.set(item, 'Statut', correct_status)
                        self.parent.video_tree.set(item, 'Progression', correct_progress)
                        self.parent.video_tree.update()
                        corrections_made += 1
                        self.parent.log(f"📝 Statut corrigé pour {day}: {correct_status}")
                    break
        
        if corrections_made > 0:
            self.parent.log(f"✅ {corrections_made} statut(s) corrigé(s)")
        
        if hasattr(self.parent, 'final_statuses'):
            self.parent.final_statuses.clear()