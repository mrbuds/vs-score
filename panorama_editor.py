#!/usr/bin/env python3
"""
Module 2 : Édition des panoramas
Version améliorée avec meilleure gestion d'erreurs
"""

from PIL import Image, ImageDraw
from tkinter import messagebox

from config import config


class PanoramaEditor:
    """Éditeur de panoramas avec fonctions de recadrage"""
    
    def __init__(self, parent):
        self.parent = parent
    
    def start_crop_drag(self, event):
        """Démarre le drag pour définir une zone à enlever"""
        if not self.parent.current_panorama:
            return
        
        canvas_y = self.parent.edit_canvas.canvasy(event.y)
        zoom = self.parent.zoom_scale.get() / 100.0
        img_y = int(canvas_y / zoom)
        
        self.parent.crop_drag_start = img_y
    
    def update_crop_drag(self, event):
        """Met à jour l'aperçu pendant le drag"""
        if not self.parent.current_panorama or self.parent.crop_drag_start is None:
            return
        
        canvas_y = self.parent.edit_canvas.canvasy(event.y)
        zoom = self.parent.zoom_scale.get() / 100.0
        img_y_current = int(canvas_y / zoom)
        img_y_start = self.parent.crop_drag_start
        
        img_height = self.parent.current_panorama.size[1]
        
        # Calculer les positions temporaires
        y_top = min(img_y_start, img_y_current)
        y_bottom = max(img_y_start, img_y_current)
        
        # Mettre à jour l'aperçu
        self.parent.crop_top.set(y_top)
        crop_bottom_amount = img_height - y_bottom
        self.parent.crop_bottom.set(crop_bottom_amount)
        
        self.parent.display_image_in_canvas()
        self.parent.edit_canvas.update_idletasks()
    
    def end_crop_drag(self, event):
        """Termine le drag et définit la zone à enlever"""
        if not self.parent.current_panorama or self.parent.crop_drag_start is None:
            return
        
        canvas_y = self.parent.edit_canvas.canvasy(event.y)
        zoom = self.parent.zoom_scale.get() / 100.0
        img_y_end = int(canvas_y / zoom)
        img_y_start = self.parent.crop_drag_start
        
        img_height = self.parent.current_panorama.size[1]
        
        # Détecter clic simple vs drag
        drag_distance = abs(img_y_end - img_y_start)
        
        if drag_distance < 10:
            # Clic simple : coupe en bas
            crop_amount = img_height - img_y_end
            
            if 0 < crop_amount < img_height:
                self.parent.crop_bottom.set(crop_amount)
                self.parent.crop_top.set(0)
                self.parent.display_image_in_canvas()
                self.parent.log(f"✂️ Ligne de coupe basse définie")
                self.parent.log(f"   Position: {img_y_end}px depuis le haut")
                self.parent.log(f"   Coupe: {crop_amount}px depuis le bas")
        else:
            # Drag : enlever la zone entre les deux lignes
            y_top = min(img_y_start, img_y_end)
            y_bottom = max(img_y_start, img_y_end)
            
            if y_top > 0 and y_bottom < img_height:
                self.parent.crop_top.set(y_top)
                crop_bottom_amount = img_height - y_bottom
                self.parent.crop_bottom.set(crop_bottom_amount)
                self.parent.display_image_in_canvas()
                self.parent.log(f"✂️ Zone à enlever définie")
                self.parent.log(f"   Haut: {y_top}px, Bas: {y_bottom}px")
                self.parent.log(f"   Hauteur à enlever: {y_bottom - y_top}px")
        
        self.parent.crop_drag_start = None
    
    def scroll_to_bottom(self):
        """Fait défiler jusqu'en bas"""
        if not self.parent.current_panorama:
            self.parent.log("ℹ️  Aucune image chargée")
            return
        
        self.parent.edit_canvas.update_idletasks()
        self.parent.edit_canvas.yview_moveto(1.0)
        self.parent.log("⬇️ Vue déplacée en bas de l'image")
    
    def scroll_to_top(self):
        """Fait défiler jusqu'en haut"""
        if not self.parent.current_panorama:
            self.parent.log("ℹ️  Aucune image chargée")
            return
        
        self.parent.edit_canvas.yview_moveto(0.0)
        self.parent.log("⬆️ Vue déplacée en haut de l'image")
    
    def fit_to_window(self):
        """Ajuste à la fenêtre"""
        if not self.parent.current_panorama:
            self.parent.log("ℹ️  Aucune image chargée")
            return
        
        self.parent.edit_canvas.update_idletasks()
        canvas_width = self.parent.edit_canvas.winfo_width()
        canvas_height = self.parent.edit_canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            img_width, img_height = self.parent.current_panorama.size
            zoom_w = (canvas_width / img_width) * 100
            zoom_h = (canvas_height / img_height) * 100
            
            optimal_zoom = min(zoom_w, zoom_h, config.zoom_max)
            optimal_zoom = max(optimal_zoom, config.zoom_min)
            
            self.parent.zoom_scale.set(int(optimal_zoom))
            self.parent.display_image_in_canvas()
            self.parent.log(f"🔍 Zoom ajusté à {int(optimal_zoom)}%")
    
    def apply_crop(self):
        """Applique le recadrage"""
        if not self.parent.current_panorama:
            self.parent.log("ℹ️  Aucune image chargée")
            return
        
        w, h = self.parent.current_panorama.size
        top = self.parent.crop_top.get()
        bottom_px = self.parent.crop_bottom.get()
        
        if top > 0 and bottom_px > 0:
            # Deux lignes : enlever ce qui est ENTRE
            y_top = top
            y_bottom = h - bottom_px
            
            if y_top >= y_bottom:
                self.parent.log("❌ Zone invalide (lignes trop proches)")
                messagebox.showerror("Erreur", "Zone invalide: les lignes sont trop proches")
                return
            
            if y_top < 0 or y_bottom > h:
                self.parent.log("❌ Zone hors limites")
                messagebox.showerror("Erreur", "Zone hors des limites de l'image")
                return
            
            old_height = h
            
            try:
                # Découper et recoller
                top_part = self.parent.current_panorama.crop((0, 0, w, y_top))
                bottom_part = self.parent.current_panorama.crop((0, y_bottom, w, h))
                
                new_height = top_part.height + bottom_part.height
                new_image = Image.new('RGB', (w, new_height))
                new_image.paste(top_part, (0, 0))
                new_image.paste(bottom_part, (0, top_part.height))
                
                self.parent.current_panorama = new_image
                self.parent.display_image_in_canvas()
                
                w, h = self.parent.current_panorama.size
                self.parent.info_label.config(text=f"Taille: {w}x{h}px")
                
                pixels_removed = old_height - h
                self.parent.log(f"✂️ Zone du milieu enlevée: {self.parent.current_day}")
                self.parent.log(f"   Enlevé de {y_top}px à {y_bottom}px")
                self.parent.log(f"   {pixels_removed}px supprimés (nouvelle hauteur: {h}px)")
            
            except Exception as e:
                self.parent.log(f"❌ Erreur lors du crop: {e}")
                messagebox.showerror("Erreur", f"Erreur lors du recadrage:\n{e}")
                return
        
        elif bottom_px > 0:
            # Une seule ligne : coupe en bas
            bottom = h - bottom_px
            
            if bottom <= 0:
                self.parent.log("❌ Paramètres invalides")
                messagebox.showerror("Erreur", "La zone de coupe est trop grande")
                return
            
            old_height = h
            
            try:
                self.parent.current_panorama = self.parent.current_panorama.crop((0, 0, w, bottom))
                self.parent.display_image_in_canvas()
                
                w, h = self.parent.current_panorama.size
                self.parent.info_label.config(text=f"Taille: {w}x{h}px")
                
                pixels_removed = old_height - h
                self.parent.log(f"✂️ Recadrage appliqué (bas): {self.parent.current_day}")
                self.parent.log(f"   {pixels_removed}px supprimés (nouvelle hauteur: {h}px)")
            
            except Exception as e:
                self.parent.log(f"❌ Erreur lors du crop: {e}")
                messagebox.showerror("Erreur", f"Erreur lors du recadrage:\n{e}")
                return
        else:
            self.parent.log("ℹ️  Aucune ligne définie")
            return
        
        # Réinitialiser
        self.parent.crop_top.set(0)
        self.parent.crop_bottom.set(0)
        self.parent.crop_drag_start = None
    
    def save_edited_panorama(self):
        """Sauvegarde le panorama édité"""
        if not self.parent.current_panorama or not self.parent.current_day:
            self.parent.log("ℹ️  Aucune image à sauvegarder")
            return
        
        try:
            output_path = self.parent.panorama_files[self.parent.current_day]
            self.parent.current_panorama.save(output_path)
            
            # Mettre à jour l'original
            self.parent.original_panorama = self.parent.current_panorama.copy()
            
            w, h = self.parent.current_panorama.size
            self.parent.log(f"💾 Sauvegardé: {self.parent.current_day}.png ({w}x{h}px)")
            
            # Notification visuelle
            self.parent.info_label.config(text=f"✅ Sauvegardé!\nTaille: {w}x{h}px")
            self.parent.root.after(2000, lambda: self.parent.info_label.config(text=f"Taille: {w}x{h}px"))
        
        except PermissionError:
            self.parent.log(f"❌ Permission refusée pour sauvegarder")
            messagebox.showerror("Erreur", "Permission refusée pour sauvegarder le fichier")
        
        except IOError as e:
            self.parent.log(f"❌ Erreur I/O: {e}")
            messagebox.showerror("Erreur", f"Erreur d'écriture:\n{e}")
        
        except Exception as e:
            self.parent.log(f"❌ Erreur lors de la sauvegarde: {e}")
            messagebox.showerror("Erreur", f"Impossible de sauvegarder:\n{e}")
    
    def undo_changes(self):
        """Annule les modifications"""
        if not self.parent.original_panorama:
            self.parent.log("ℹ️  Rien à annuler")
            return
        
        self.parent.current_panorama = self.parent.original_panorama.copy()
        self.parent.crop_top.set(0)
        self.parent.crop_bottom.set(0)
        self.parent.crop_drag_start = None
        self.parent.display_image_in_canvas()
        
        w, h = self.parent.current_panorama.size
        self.parent.info_label.config(text=f"Taille: {w}x{h}px")
        
        self.parent.log("↩️  Modifications annulées")
    
    def zoom_image(self, event):
        """Zoom avec la molette"""
        if not self.parent.current_panorama:
            return
        
        current = self.parent.zoom_scale.get()
        if event.delta > 0:
            new_zoom = min(config.zoom_max, current + config.zoom_step)
        else:
            new_zoom = max(config.zoom_min, current - config.zoom_step)
        
        self.parent.zoom_scale.set(new_zoom)
        self.parent.display_image_in_canvas()
    
    def start_pan(self, event):
        """Démarre le déplacement"""
        self.parent.edit_canvas.scan_mark(event.x, event.y)
    
    def pan_image(self, event):
        """Déplace l'image"""
        self.parent.edit_canvas.scan_dragto(event.x, event.y, gain=1)
