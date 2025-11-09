#!/usr/bin/env python3
"""
Module 2 : Édition des panoramas (simplifié sans détection auto)
"""

from PIL import Image, ImageDraw
import numpy as np
from tkinter import messagebox

class PanoramaEditor:
    def __init__(self, parent):
        self.parent = parent
    
    def set_crop_line(self, event):
        """Définit la ligne de coupe avec un clic droit"""
        if not self.parent.current_panorama:
            return
        
        canvas_y = self.parent.edit_canvas.canvasy(event.y)
        zoom = self.parent.zoom_scale.get() / 100.0
        img_y = int(canvas_y / zoom)
        
        img_height = self.parent.current_panorama.size[1]
        crop_amount = img_height - img_y
        
        if 0 < crop_amount < img_height:
            self.parent.crop_bottom.set(min(crop_amount, 2000))
            self.parent.display_image_in_canvas()
            self.parent.log(f"✂️ Ligne de coupe définie par clic droit")
            self.parent.log(f"   Position: {img_y}px depuis le haut")
            self.parent.log(f"   Coupe: {crop_amount}px depuis le bas")
    
    def scroll_to_bottom(self):
        """Fait défiler jusqu'en bas"""
        if not self.parent.current_panorama:
            messagebox.showinfo("Info", "Aucune image chargée")
            return
        
        self.parent.edit_canvas.update_idletasks()
        self.parent.edit_canvas.yview_moveto(1.0)
        self.parent.log("⬇️ Vue déplacée en bas de l'image")
    
    def scroll_to_top(self):
        """Fait défiler jusqu'en haut"""
        if not self.parent.current_panorama:
            messagebox.showinfo("Info", "Aucune image chargée")
            return
        
        self.parent.edit_canvas.yview_moveto(0.0)
        self.parent.log("⬆️ Vue déplacée en haut de l'image")
    
    def fit_to_window(self):
        """Ajuste à la fenêtre"""
        if not self.parent.current_panorama:
            return
        
        self.parent.edit_canvas.update_idletasks()
        canvas_width = self.parent.edit_canvas.winfo_width()
        canvas_height = self.parent.edit_canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            img_width, img_height = self.parent.current_panorama.size
            zoom_w = (canvas_width / img_width) * 100
            zoom_h = (canvas_height / img_height) * 100
            
            optimal_zoom = min(zoom_w, zoom_h, 100)
            
            self.parent.zoom_scale.set(int(optimal_zoom))
            self.parent.display_image_in_canvas()
            self.parent.log(f"🔍 Zoom ajusté à {int(optimal_zoom)}%")
    
    def apply_crop(self):
        """Applique le recadrage"""
        if not self.parent.current_panorama:
            return
            
        w, h = self.parent.current_panorama.size
        top = self.parent.crop_top.get()
        bottom = h - self.parent.crop_bottom.get()
        
        if top >= bottom:
            messagebox.showerror("Erreur", "Paramètres de recadrage invalides")
            return
            
        self.parent.current_panorama = self.parent.current_panorama.crop((0, top, w, bottom))
        self.parent.display_image_in_canvas()
        
        w, h = self.parent.current_panorama.size
        self.parent.info_label.config(text=f"Taille: {w}x{h}px")
        
        self.parent.log(f"Recadrage appliqué: {self.parent.current_day}")
    
    def save_edited_panorama(self):
        """Sauvegarde le panorama édité"""
        if not self.parent.current_panorama or not self.parent.current_day:
            return
            
        result = messagebox.askyesno("Sauvegarder", 
                                     f"Remplacer le fichier {self.parent.current_day}.png?")
        if result:
            self.parent.current_panorama.save(self.parent.panorama_files[self.parent.current_day])
            self.parent.log(f"Sauvegardé: {self.parent.current_day}.png")
            messagebox.showinfo("Succès", "Panorama sauvegardé")
    
    def undo_changes(self):
        """Annule les modifications"""
        if self.parent.original_panorama:
            self.parent.current_panorama = self.parent.original_panorama.copy()
            self.parent.crop_top.set(0)
            self.parent.crop_bottom.set(0)
            self.parent.display_image_in_canvas()
            self.parent.log("Modifications annulées")
    
    def zoom_image(self, event):
        """Zoom avec la molette"""
        if event.delta > 0:
            new_zoom = min(200, self.parent.zoom_scale.get() + 10)
        else:
            new_zoom = max(10, self.parent.zoom_scale.get() - 10)
        self.parent.zoom_scale.set(new_zoom)
        self.parent.display_image_in_canvas()
    
    def start_pan(self, event):
        """Démarre le déplacement"""
        self.parent.edit_canvas.scan_mark(event.x, event.y)
    
    def pan_image(self, event):
        """Déplace l'image"""
        self.parent.edit_canvas.scan_dragto(event.x, event.y, gain=1)