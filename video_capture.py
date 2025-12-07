#!/usr/bin/env python3
"""
Module 0 : Capture vidéo de zone d'écran
Version améliorée avec meilleure gestion d'erreurs
"""

import tkinter as tk
from tkinter import messagebox
import cv2
import numpy as np
from pathlib import Path
import threading
import time

from config import config

try:
    import mss
    import mss.exception
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


class RegionSelector:
    """Overlay avec cadre persistant et boutons de contrôle flottants"""
    
    def __init__(self, callback):
        self.callback = callback
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.region = None
        self.selecting = True
        self.frame_window = None
        self.button_window = None
        
        # Créer fenêtre overlay fullscreen
        self.root = tk.Toplevel()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-alpha', 0.3)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        
        # Canvas pour dessiner
        self.canvas = tk.Canvas(self.root, cursor='cross', bg='black', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        
        # Bindings pour la sélection
        self.canvas.bind('<Button-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.root.bind('<Escape>', lambda e: self.cancel())
        
        # Instructions
        self.instructions = self.canvas.create_text(
            self.root.winfo_screenwidth() // 2, 50,
            text="Cliquez et glissez pour sélectionner la zone à capturer\nAppuyez sur Échap pour annuler",
            fill='white', font=('Arial', 16, 'bold'), tags='instructions'
        )
    
    def on_press(self, event):
        if not self.selecting:
            return
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
    
    def on_drag(self, event):
        if not self.selecting:
            return
        if self.rect:
            self.canvas.delete(self.rect)
        # Bordure fine en pointillés jaunes
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline='#FFD700', width=2, dash=(5, 5)
        )
    
    def on_release(self, event):
        if not self.selecting:
            return
        
        if self.start_x and self.start_y:
            x1 = min(self.start_x, event.x)
            y1 = min(self.start_y, event.y)
            x2 = max(self.start_x, event.x)
            y2 = max(self.start_y, event.y)
            
            width = x2 - x1
            height = y2 - y1
            
            if width > 50 and height > 50:
                self.region = (x1, y1, width, height)
                self.selecting = False
                
                # Fermer l'overlay fullscreen
                self.root.destroy()
                
                # Créer un petit canvas pour le rectangle
                self.frame_window = tk.Toplevel()
                self.frame_window.overrideredirect(True)
                self.frame_window.attributes('-topmost', True)
                self.frame_window.geometry(f"{width+10}x{height+10}+{x1-5}+{y1-5}")
                self.frame_window.attributes('-transparentcolor', 'black')
                
                # Canvas noir (sera transparent)
                frame_canvas = tk.Canvas(
                    self.frame_window, width=width+10, height=height+10,
                    bg='black', highlightthickness=0
                )
                frame_canvas.pack()
                
                # Rectangle en pointillés
                self.rect = frame_canvas.create_rectangle(
                    5, 5, width+5, height+5,
                    outline='#FFD700', width=2, dash=(5, 5)
                )
                
                # Boutons de contrôle
                self.create_control_buttons(x1, y2)
            else:
                # Zone trop petite
                if self.rect:
                    self.canvas.delete(self.rect)
                self.start_x = None
                self.start_y = None
    
    def create_control_buttons(self, x, y):
        """Crée les boutons de contrôle sous le cadre"""
        button_y = y + 10
        button_x = x
        
        self.button_window = tk.Toplevel()
        self.button_window.overrideredirect(True)
        self.button_window.attributes('-topmost', True)
        self.button_window.geometry(f"280x45+{button_x}+{button_y}")
        self.button_window.configure(bg='#2b2b2b')
        
        button_frame = tk.Frame(self.button_window, bg='#2b2b2b', padx=6, pady=6)
        button_frame.pack(fill='both', expand=True)
        
        # Bouton Démarrer
        self.start_button = tk.Button(
            button_frame, text="▶",
            command=self.start_recording,
            bg='#4CAF50', fg='white', font=('Arial', 14, 'bold'),
            padx=8, pady=2, cursor='hand2', relief='flat', width=2
        )
        self.start_button.pack(side='left', padx=2)
        
        # Bouton Arrêter
        self.stop_button = tk.Button(
            button_frame, text="⏹",
            command=self.stop_recording,
            bg='#f44336', fg='white', font=('Arial', 14, 'bold'),
            padx=8, pady=2, cursor='hand2', relief='flat', width=2,
            state='disabled'
        )
        self.stop_button.pack(side='left', padx=2)
        
        # Bouton Annuler
        self.cancel_button = tk.Button(
            button_frame, text="❌",
            command=self.cancel,
            bg='#FF9800', fg='white', font=('Arial', 12, 'bold'),
            padx=6, pady=2, cursor='hand2', relief='flat', width=2
        )
        self.cancel_button.pack(side='left', padx=2)
        
        # Label de statut
        self.status_label = tk.Label(
            button_frame, text="Prêt",
            bg='#2b2b2b', fg='white', font=('Arial', 7)
        )
        self.status_label.pack(side='left', padx=4)
    
    def start_recording(self):
        """Démarre l'enregistrement"""
        if self.region:
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self.status_label.config(text="🔴 Enregistrement...")
            self.callback('start', self.region)
    
    def stop_recording(self):
        """Arrête l'enregistrement"""
        self.start_button.config(state='disabled')
        self.stop_button.config(state='disabled')
        self.cancel_button.config(state='disabled')
        self.status_label.config(text="💾 Sauvegarde...")
        self.callback('stop', self.region)
        self.root.after(500, self.close)
    
    def cancel(self):
        """Annule la sélection ou l'enregistrement"""
        self.callback('cancel', self.region)
        self.close()
    
    def close(self):
        """Ferme l'overlay"""
        for window in [self.button_window, self.frame_window]:
            if window:
                try:
                    window.destroy()
                except tk.TclError:
                    pass
        
        if hasattr(self, 'root'):
            try:
                self.root.destroy()
            except tk.TclError:
                pass
    
    def update_status(self, text):
        """Met à jour le statut"""
        if hasattr(self, 'status_label'):
            try:
                self.status_label.config(text=text)
            except tk.TclError:
                pass


class VideoCapture:
    """Gère la capture vidéo d'une zone d'écran"""
    
    def __init__(self, parent):
        self.parent = parent
        self.recording = False
        self.region = None
        self.output_folder = Path.cwd()
        self.writer = None
        self.monitor = None
        self.fps = config.default_fps
        self.record_thread = None
        self.start_time = None
        self.frame_count = 0
        self.region_selector = None
        self.current_output_path = None
        self._recording_lock = threading.Lock()
    
    def select_region(self):
        """Ouvre l'overlay pour sélectionner la zone"""
        if self.recording:
            messagebox.showwarning(
                "Enregistrement en cours",
                "Arrêtez l'enregistrement avant de changer la zone"
            )
            return
        
        self.region_selector = RegionSelector(self.on_region_action)
    
    def on_region_action(self, action, region):
        """Callback quand l'utilisateur interagit avec l'overlay"""
        if action == 'start':
            self.region = region
            self.parent.on_capture_start(region)
        elif action == 'stop':
            self.stop_recording()
            self.parent.on_capture_stop()
        elif action == 'cancel':
            if self.recording:
                self.cancel_recording()
                self.parent.on_capture_cancel()
            self.region_selector = None
    
    def start_recording(self, output_path):
        """Démarre l'enregistrement"""
        if not MSS_AVAILABLE:
            if self.region_selector:
                self.region_selector.update_status("❌ Module mss manquant")
            messagebox.showerror(
                "Erreur",
                "Module 'mss' non installé.\nInstallez-le avec: pip install mss"
            )
            return False
        
        if not self.region:
            if self.region_selector:
                self.region_selector.update_status("❌ Aucune zone")
            return False
        
        with self._recording_lock:
            if self.recording:
                return False
        
        try:
            # Ajuster pour exclure le cadre
            border_margin = 4
            capture_x = self.region[0] + border_margin
            capture_y = self.region[1] + border_margin
            capture_width = self.region[2] - (border_margin * 2)
            capture_height = self.region[3] - (border_margin * 2)
            
            self.monitor = {
                'left': capture_x,
                'top': capture_y,
                'width': capture_width,
                'height': capture_height
            }
            
            # Créer le writer vidéo
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(
                str(output_path),
                fourcc,
                self.fps,
                (capture_width, capture_height)
            )
            
            if not self.writer.isOpened():
                raise IOError("Impossible de créer le fichier vidéo")
            
            # Variables de suivi
            with self._recording_lock:
                self.recording = True
            self.start_time = time.time()
            self.frame_count = 0
            self.current_output_path = output_path
            
            # Démarrer le thread d'enregistrement
            self.record_thread = threading.Thread(target=self._record_loop, daemon=True)
            self.record_thread.start()
            
            self.parent.log(f"🔴 Enregistrement démarré: {output_path.name}")
            return True
        
        except IOError as e:
            self.parent.log(f"❌ Erreur I/O: {e}")
            if self.region_selector:
                self.region_selector.update_status(f"❌ I/O: {str(e)[:15]}")
            self.cleanup()
            return False
        
        except cv2.error as e:
            self.parent.log(f"❌ Erreur OpenCV: {e}")
            if self.region_selector:
                self.region_selector.update_status("❌ Erreur OpenCV")
            self.cleanup()
            return False
        
        except Exception as e:
            self.parent.log(f"❌ Erreur inattendue: {type(e).__name__}: {e}")
            if self.region_selector:
                self.region_selector.update_status(f"❌ {type(e).__name__}")
            self.cleanup()
            return False
    
    def _record_loop(self):
        """Boucle d'enregistrement (thread séparé)"""
        sct = None
        try:
            import mss as mss_module
            sct = mss_module.mss()
            
            while True:
                with self._recording_lock:
                    if not self.recording:
                        break
                
                # Capturer l'écran
                screenshot = sct.grab(self.monitor)
                
                # Convertir en numpy array BGR
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                # Écrire la frame
                self.writer.write(frame)
                self.frame_count += 1
                
                # Mise à jour UI périodique
                if self.frame_count % 30 == 0:
                    elapsed = time.time() - self.start_time
                    
                    if self.region_selector:
                        minutes = int(elapsed // 60)
                        seconds = int(elapsed % 60)
                        self.region_selector.update_status(f"🔴 {minutes:02d}:{seconds:02d}")
                
                # Contrôler le FPS
                time.sleep(1.0 / self.fps)
        
        except mss.exception.ScreenShotError as e:
            self.parent.log(f"❌ Erreur capture écran: {e}")
            with self._recording_lock:
                self.recording = False
        
        except cv2.error as e:
            self.parent.log(f"❌ Erreur OpenCV: {e}")
            with self._recording_lock:
                self.recording = False
        
        except Exception as e:
            self.parent.log(f"❌ Erreur enregistrement: {type(e).__name__}: {e}")
            with self._recording_lock:
                self.recording = False
        
        finally:
            if sct:
                try:
                    sct.close()
                except Exception:
                    pass
    
    def stop_recording(self):
        """Arrête l'enregistrement et sauvegarde"""
        with self._recording_lock:
            if not self.recording:
                return False
            self.recording = False
        
        # Attendre la fin du thread
        if self.record_thread:
            self.record_thread.join(timeout=3)
            if self.record_thread.is_alive():
                self.parent.log("⚠️ Le thread ne s'est pas arrêté proprement")
        
        # Petit délai pour s'assurer que tout est écrit
        time.sleep(0.2)
        
        # Finaliser
        elapsed = time.time() - self.start_time if self.start_time else 0
        self.cleanup()
        
        self.parent.log(f"⏹️ Enregistrement arrêté: {self.frame_count} frames en {elapsed:.1f}s")
        self.parent.log(f"💾 Sauvegardé: {self.current_output_path}")
        
        return True
    
    def cancel_recording(self):
        """Annule l'enregistrement sans sauvegarder"""
        with self._recording_lock:
            if not self.recording:
                return False
            self.recording = False
        
        # Attendre la fin du thread
        if self.record_thread:
            self.record_thread.join(timeout=2)
        
        # Nettoyer
        self.cleanup()
        
        # Supprimer le fichier
        if self.current_output_path and self.current_output_path.exists():
            try:
                self.current_output_path.unlink()
                self.parent.log("🗑️ Enregistrement annulé et fichier supprimé")
            except PermissionError:
                self.parent.log("⚠️ Enregistrement annulé (fichier non supprimé - permission)")
            except Exception as e:
                self.parent.log(f"⚠️ Enregistrement annulé (fichier non supprimé: {e})")
        
        return True
    
    def cleanup(self):
        """Nettoie les ressources"""
        if self.writer:
            try:
                self.writer.release()
                self.parent.log("📝 Writer vidéo fermé")
            except Exception as e:
                self.parent.log(f"⚠️ Erreur fermeture writer: {e}")
            self.writer = None
    
    def set_output_folder(self, folder):
        """Définit le dossier de sortie"""
        self.output_folder = Path(folder)
        self.parent.log(f"📁 Dossier de sortie: {folder}")
    
    def set_fps(self, fps):
        """Définit le FPS de capture"""
        with self._recording_lock:
            if not self.recording:
                self.fps = max(config.min_fps, min(fps, config.max_fps))
                self.parent.log(f"🎞️ FPS réglé à: {self.fps}")
