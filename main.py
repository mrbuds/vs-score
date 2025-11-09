#!/usr/bin/env python3
"""
Interface Last War - Fichier principal
Utilise les modules pour une meilleure organisation
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw, ImageFont
from datetime import datetime
import subprocess
import sys
import queue

# Importer les modules
from video_processor import VideoProcessor
from panorama_editor import PanoramaEditor

class LastWarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Last War - Traitement des tableaux de scores")
        self.root.geometry("1200x800")
        
        # Variables
        self.video_files = {}
        self.panorama_files = {}
        self.current_panorama = None
        self.original_panorama = None
        self.current_day = None
        self.crop_lines = []
        self.enable_ocr = tk.BooleanVar(value=False)
        self.update_queue = queue.Queue()
        self.final_statuses = {}
        
        # Configuration
        self.days = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi']
        self.all_days = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'semaine']
        
        # Modules
        self.video_processor = VideoProcessor(self)
        self.panorama_editor = PanoramaEditor(self)
        
        self.setup_ui()
        self.check_update_queue()
        
    def setup_ui(self):
        """Crée l'interface utilisateur"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.video_tab = ttk.Frame(notebook)
        notebook.add(self.video_tab, text="1. Vidéos → Panoramas")
        self.setup_video_tab()
        
        self.edit_tab = ttk.Frame(notebook)
        notebook.add(self.edit_tab, text="2. Édition des panoramas")
        self.setup_edit_tab()
        
        self.concat_tab = ttk.Frame(notebook)
        notebook.add(self.concat_tab, text="3. Tableau final")
        self.setup_concat_tab()
        
        self.status_bar = ttk.Label(self.root, text="Prêt", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_video_tab(self):
        """Onglet 1 avec traitement parallèle"""
        list_frame = ttk.LabelFrame(self.video_tab, text="Vidéos à traiter")
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('Jour', 'Fichier', 'Statut', 'Progression')
        self.video_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.video_tree.heading(col, text=col)
        
        self.video_tree.column('Jour', width=100)
        self.video_tree.column('Fichier', width=300)
        self.video_tree.column('Statut', width=150)
        self.video_tree.column('Progression', width=100)
        
        self.video_tree.pack(side=tk.LEFT, fill='both', expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.video_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill='y')
        self.video_tree.configure(yscrollcommand=scrollbar.set)
        
        # Options
        options_frame = ttk.LabelFrame(self.video_tab, text="Options de traitement")
        options_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(options_frame, text="🚀 Workers parallèles:").grid(row=0, column=0, padx=5, pady=5)
        self.max_workers = tk.IntVar(value=3)
        ttk.Spinbox(options_frame, from_=1, to=6, textvariable=self.max_workers, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(options_frame, text="Seuil de qualité:").grid(row=1, column=0, padx=5, pady=5)
        self.quality_threshold = tk.Scale(options_frame, from_=0.5, to=1.0, resolution=0.05, orient=tk.HORIZONTAL, length=200)
        self.quality_threshold.set(0.8)
        self.quality_threshold.grid(row=1, column=1, columnspan=2, padx=5, pady=5)
        
        ttk.Label(options_frame, text="Hauteur template:").grid(row=2, column=0, padx=5, pady=5)
        self.template_height = tk.Scale(options_frame, from_=50, to=200, resolution=10, orient=tk.HORIZONTAL, length=200)
        self.template_height.set(100)
        self.template_height.grid(row=2, column=1, columnspan=2, padx=5, pady=5)
        
        # Boutons
        control_frame = ttk.Frame(self.video_tab)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(control_frame, text="📁 Charger vidéos", command=self.load_videos).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="▶️ Traiter sélection", command=self.video_processor.process_selected_videos).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="⚡ Traiter tout", command=self.video_processor.process_all_videos).pack(side=tk.LEFT, padx=5)
        
        # Journal
        log_frame = ttk.LabelFrame(self.video_tab, text="Journal")
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8)
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
        
    def setup_edit_tab(self):
        """Onglet 2 avec toutes les améliorations"""
        select_frame = ttk.Frame(self.edit_tab)
        select_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(select_frame, text="Jour:").pack(side=tk.LEFT, padx=5)
        self.day_combo = ttk.Combobox(select_frame, values=self.days, state='readonly')
        self.day_combo.pack(side=tk.LEFT, padx=5)
        self.day_combo.bind('<<ComboboxSelected>>', self.load_panorama_for_edit)
        
        ttk.Button(select_frame, text="📁 Charger panoramas", command=self.load_panoramas).pack(side=tk.LEFT, padx=20)
        
        main_frame = ttk.Frame(self.edit_tab)
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Canvas avec scrollbars
        canvas_frame = ttk.LabelFrame(main_frame, text="Aperçu (scroll pour zoomer, clic droit pour ligne de coupe)")
        canvas_frame.pack(side=tk.LEFT, fill='both', expand=True)
        
        self.edit_canvas = tk.Canvas(canvas_frame, bg='gray')
        self.edit_canvas.pack(fill='both', expand=True)
        
        h_scroll = ttk.Scrollbar(canvas_frame, orient='horizontal', command=self.edit_canvas.xview)
        h_scroll.pack(side=tk.BOTTOM, fill='x')
        v_scroll = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.edit_canvas.yview)
        v_scroll.pack(side=tk.RIGHT, fill='y')
        
        self.edit_canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        
        # Panneau de contrôle
        control_panel = ttk.Frame(main_frame)
        control_panel.pack(side=tk.RIGHT, fill='y', padx=10)
        
        # Recadrage avec limites 2000px et incrément 10
        crop_frame = ttk.LabelFrame(control_panel, text="Recadrage")
        crop_frame.pack(fill='x', pady=10)
        
        ttk.Label(crop_frame, text="Couper en bas:").grid(row=0, column=0, padx=5, pady=5)
        self.crop_bottom = tk.IntVar(value=0)
        ttk.Spinbox(crop_frame, from_=0, to=2000, increment=10, textvariable=self.crop_bottom, width=10, command=self.update_crop_preview).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(crop_frame, text="Couper en haut:").grid(row=1, column=0, padx=5, pady=5)
        self.crop_top = tk.IntVar(value=0)
        ttk.Spinbox(crop_frame, from_=0, to=2000, increment=10, textvariable=self.crop_top, width=10, command=self.update_crop_preview).grid(row=1, column=1, padx=5, pady=5)
        
        # Boutons d'action (sans détection auto)
        ttk.Button(crop_frame, text="⬇️ Aller en bas", command=self.panorama_editor.scroll_to_bottom).grid(row=2, column=0, pady=3)
        ttk.Button(crop_frame, text="⬆️ Aller en haut", command=self.panorama_editor.scroll_to_top).grid(row=2, column=1, pady=3)
        ttk.Button(crop_frame, text="📏 Ajuster à la fenêtre", command=self.panorama_editor.fit_to_window).grid(row=3, column=0, columnspan=2, pady=3)
        
        # Zoom
        zoom_frame = ttk.LabelFrame(control_panel, text="Zoom")
        zoom_frame.pack(fill='x', pady=10)
        
        self.zoom_scale = tk.Scale(zoom_frame, from_=10, to=200, orient=tk.HORIZONTAL, label="%", command=self.set_zoom)
        self.zoom_scale.set(100)
        self.zoom_scale.pack(fill='x', padx=5, pady=5)
        
        # Actions
        action_frame = ttk.LabelFrame(control_panel, text="Actions")
        action_frame.pack(fill='x', pady=10)
        
        ttk.Button(action_frame, text="✂️ Appliquer recadrage", command=self.panorama_editor.apply_crop).pack(fill='x', padx=5, pady=5)
        ttk.Button(action_frame, text="↩️ Annuler", command=self.panorama_editor.undo_changes).pack(fill='x', padx=5, pady=5)
        ttk.Button(action_frame, text="💾 Sauvegarder", command=self.panorama_editor.save_edited_panorama).pack(fill='x', padx=5, pady=5)
        
        self.info_label = ttk.Label(control_panel, text="Aucune image chargée", wraplength=200)
        self.info_label.pack(pady=10)
        
        # Bindings IMPORTANTS
        self.edit_canvas.bind("<Button-3>", self.panorama_editor.set_crop_line)  # Clic droit
        self.edit_canvas.bind("<MouseWheel>", self.panorama_editor.zoom_image)
        self.edit_canvas.bind("<Button-1>", self.panorama_editor.start_pan)
        self.edit_canvas.bind("<B1-Motion>", self.panorama_editor.pan_image)
        
    def setup_concat_tab(self):
        """Onglet 3 - Tableau final"""
        preview_frame = ttk.LabelFrame(self.concat_tab, text="Aperçu du tableau final")
        preview_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.concat_canvas = tk.Canvas(preview_frame, bg='gray')
        self.concat_canvas.pack(fill='both', expand=True)
        
        control_frame = ttk.Frame(self.concat_tab)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(control_frame, text="Générer aperçu", command=self.preview_concatenation).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Sauvegarder tableau final", command=self.save_final_table).pack(side=tk.LEFT, padx=5)
    
    def check_update_queue(self):
        """Vérifie la queue de mises à jour"""
        updates_processed = 0
        max_updates = 30
        
        try:
            while updates_processed < max_updates:
                item = self.update_queue.get_nowait()
                updates_processed += 1
                
                if item[0] == 'log':
                    self.log(item[1])
                elif item[0] == 'status':
                    day, status, progress = item[1], item[2], item[3]
                    for tree_item in self.video_tree.get_children():
                        if self.video_tree.item(tree_item)['values'][0] == day:
                            self.video_tree.set(tree_item, 'Statut', status)
                            self.video_tree.set(tree_item, 'Progression', progress)
                            self.video_tree.update_idletasks()
                            if '✅' in status or '❌' in status:
                                self.final_statuses[day] = (status, progress)
                            break
                elif item[0] == 'final':
                    day, success = item[1], item[2]
                    status = '✅ Terminé' if success else '❌ Échec'
                    progress = '100%' if success else ''
                    for tree_item in self.video_tree.get_children():
                        if self.video_tree.item(tree_item)['values'][0] == day:
                            self.video_tree.set(tree_item, 'Statut', status)
                            self.video_tree.set(tree_item, 'Progression', progress)
                            break
                    self.final_statuses[day] = (status, progress)
                elif item[0] == 'error':
                    day, error = item[1], item[2]
                    self.log(f"❌ Erreur {day}: {error}")
        except queue.Empty:
            pass
        
        interval = 25 if hasattr(self.video_processor, 'processing_active') and self.video_processor.processing_active else 100
        self.root.after(interval, self.check_update_queue)
    
    def log(self, message):
        """Ajoute un message au journal"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_status(self, message):
        """Met à jour la barre de statut"""
        self.status_bar.config(text=message)
        self.root.update_idletasks()
    
    def load_videos(self):
        """Charge les fichiers vidéo"""
        files = filedialog.askopenfilenames(title="Sélectionner les vidéos", filetypes=[("Vidéos", "*.mp4 *.avi *.mov *.mkv"), ("Tous", "*.*")])
        
        if not files:
            return
            
        for item in self.video_tree.get_children():
            self.video_tree.delete(item)
        self.video_files.clear()
        
        for filepath in files:
            path = Path(filepath)
            day = self.detect_day_from_filename(path.stem)
            
            if not day:
                day = self.ask_day_for_file(path.name)
                if not day:
                    continue
            
            self.video_files[day] = path
            self.video_tree.insert('', 'end', values=(day, path.name, "En attente", ""))
            
        self.log(f"📁 Chargé {len(self.video_files)} vidéo(s)")
    
    def detect_day_from_filename(self, filename):
        """Détecte le jour depuis le nom"""
        filename_lower = filename.lower()
        # Vérifier d'abord 'semaine' spécifiquement
        if 'semaine' in filename_lower:
            return 'semaine'
        # Puis vérifier les autres jours
        for day in self.days:
            if day in filename_lower:
                return day
        return None
    
    def ask_day_for_file(self, filename):
        """Demande le jour pour un fichier"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Sélection du jour")
        dialog.geometry("300x150")
        
        ttk.Label(dialog, text=f"Fichier: {filename}\nJour:").pack(pady=10)
        
        day_var = tk.StringVar()
        combo = ttk.Combobox(dialog, textvariable=day_var, values=self.all_days, state='readonly')
        combo.pack(pady=10)
        combo.current(0)
        
        result = {'day': None}
        
        def on_ok():
            result['day'] = day_var.get()
            dialog.destroy()
            
        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=10)
        dialog.wait_window()
        return result['day']
    
    def load_panoramas(self):
        """Charge des panoramas existants"""
        directory = filedialog.askdirectory(title="Sélectionner le dossier des panoramas")
        if not directory:
            return
            
        directory = Path(directory)
        self.panorama_files.clear()
        
        for day in self.all_days:
            img_path = directory / f"{day}.png"
            if img_path.exists():
                self.panorama_files[day] = img_path
                self.log(f"Chargé: {day}.png")
                
        available_days = list(self.panorama_files.keys())
        self.day_combo['values'] = available_days
        if available_days:
            self.day_combo.current(0)
            
        self.log(f"📁 Chargé {len(self.panorama_files)} panorama(s)")
    
    def load_panorama_for_edit(self, event=None):
        """Charge un panorama pour l'édition"""
        day = self.day_combo.get()
        if not day or day not in self.panorama_files:
            return
            
        self.current_day = day
        img_path = self.panorama_files[day]
        
        self.current_panorama = Image.open(img_path)
        self.original_panorama = self.current_panorama.copy()
        
        self.crop_bottom.set(0)
        self.crop_top.set(0)
        
        self.display_image_in_canvas()
        
        w, h = self.current_panorama.size
        self.info_label.config(text=f"Taille: {w}x{h}px")
        
        self.log(f"Chargé pour édition: {day}")
    
    def display_image_in_canvas(self):
        """Affiche l'image dans le canvas"""
        if not self.current_panorama:
            return
            
        zoom = self.zoom_scale.get() / 100.0
        w, h = self.current_panorama.size
        new_w = int(w * zoom)
        new_h = int(h * zoom)
        
        resized = self.current_panorama.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        if self.crop_top.get() > 0 or self.crop_bottom.get() > 0:
            draw = ImageDraw.Draw(resized)
            if self.crop_top.get() > 0:
                y = int(self.crop_top.get() * zoom)
                draw.line([(0, y), (new_w, y)], fill='red', width=2)
            if self.crop_bottom.get() > 0:
                y = new_h - int(self.crop_bottom.get() * zoom)
                draw.line([(0, y), (new_w, y)], fill='red', width=2)
        
        self.photo = ImageTk.PhotoImage(resized)
        self.edit_canvas.delete("all")
        self.edit_canvas.create_image(0, 0, anchor='nw', image=self.photo)
        self.edit_canvas.config(scrollregion=self.edit_canvas.bbox("all"))
    
    def update_crop_preview(self):
        """Met à jour l'aperçu"""
        self.display_image_in_canvas()
    
    def set_zoom(self, value):
        """Applique le zoom"""
        self.display_image_in_canvas()
    
    def preview_concatenation(self):
        """Aperçu de la concaténation avec support du zoom"""
        if not self.panorama_files:
            messagebox.showwarning("Aucun panorama", "Veuillez d'abord charger des panoramas")
            return
            
        self.log("Génération de l'aperçu du tableau final...")
        
        images = []
        for day in self.days:
            if day in self.panorama_files:
                img = Image.open(self.panorama_files[day])
                images.append(img)
                
        if not images:
            return
            
        max_height = max(img.height for img in images)
        total_width = sum(img.width for img in images)
        
        # Créer l'image résultat
        self.concat_result_image = Image.new('RGBA', (total_width, max_height), (255, 255, 255, 255))
        
        x_offset = 0
        for img in images:
            self.concat_result_image.paste(img, (x_offset, 0))
            x_offset += img.width
            
        # Mettre à jour les infos si le label existe
        if hasattr(self, 'concat_info_label') and self.concat_info_label:
            self.concat_info_label.config(text=f"Taille: {total_width}x{max_height}px\n{len(images)} images")
        
        # Afficher avec le zoom actuel
        self.display_concat_image()
        
        self.log(f"✅ Aperçu généré: {len(images)} images, {total_width}x{max_height}px")
    
    def display_concat_image(self):
        """Affiche l'image de concaténation avec le zoom actuel"""
        if not self.concat_result_image:
            return
            
        # Utiliser le zoom par défaut si le scale n'existe pas encore
        if hasattr(self, 'concat_zoom_scale') and self.concat_zoom_scale:
            zoom = self.concat_zoom_scale.get() / 100.0
        else:
            zoom = 1.0
        
        orig_width, orig_height = self.concat_result_image.size
        new_width = int(orig_width * zoom)
        new_height = int(orig_height * zoom)
        
        # Redimensionner l'image
        resized = self.concat_result_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convertir en PhotoImage
        self.concat_photo = ImageTk.PhotoImage(resized)
        
        # Afficher dans le canvas
        self.concat_canvas.delete("all")
        self.concat_canvas.create_image(0, 0, anchor='nw', image=self.concat_photo)
        self.concat_canvas.config(scrollregion=self.concat_canvas.bbox("all"))
    
    def set_concat_zoom(self, value):
        """Applique le zoom depuis le slider"""
        if self.concat_result_image:
            self.display_concat_image()
    
    def zoom_concat_image(self, event):
        """Zoom avec la molette de la souris"""
        if not self.concat_result_image:
            return
            
        # Déterminer la direction du zoom
        if event.delta > 0:
            new_zoom = min(200, self.concat_zoom_scale.get() + 10)
        else:
            new_zoom = max(10, self.concat_zoom_scale.get() - 10)
            
        self.concat_zoom_scale.set(new_zoom)
        self.display_concat_image()
    
    def fit_concat_to_window(self):
        """Ajuste l'image de concaténation à la fenêtre"""
        if not self.concat_result_image:
            messagebox.showinfo("Info", "Veuillez d'abord générer un aperçu")
            return
            
        # Obtenir la taille du canvas
        self.concat_canvas.update_idletasks()
        canvas_width = self.concat_canvas.winfo_width()
        canvas_height = self.concat_canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            # Calculer le zoom optimal
            img_width, img_height = self.concat_result_image.size
            zoom_w = (canvas_width / img_width) * 100
            zoom_h = (canvas_height / img_height) * 100
            
            # Utiliser le plus petit zoom pour que tout rentre
            optimal_zoom = min(zoom_w, zoom_h, 100)
            
            self.concat_zoom_scale.set(int(optimal_zoom))
            self.display_concat_image()
            self.log(f"🔍 Zoom ajusté à {int(optimal_zoom)}%")
    
    def start_concat_pan(self, event):
        """Démarre le déplacement dans le canvas de concaténation"""
        self.concat_canvas.scan_mark(event.x, event.y)
    
    def pan_concat_image(self, event):
        """Déplace l'image dans le canvas de concaténation"""
        self.concat_canvas.scan_dragto(event.x, event.y, gain=1)
    
    def set_concat_zoom(self, value):
        """Applique le zoom depuis le slider"""
        if self.concat_result_image:
            self.display_concat_image()
    
    def zoom_concat_image(self, event):
        """Zoom avec la molette de la souris"""
        if not self.concat_result_image:
            return
            
        # Déterminer la direction du zoom
        if event.delta > 0:
            new_zoom = min(200, self.concat_zoom_scale.get() + 10)
        else:
            new_zoom = max(10, self.concat_zoom_scale.get() - 10)
            
        self.concat_zoom_scale.set(new_zoom)
        self.display_concat_image()
    
    def fit_concat_to_window(self):
        """Ajuste l'image de concaténation à la fenêtre"""
        if not self.concat_result_image:
            messagebox.showinfo("Info", "Veuillez d'abord générer un aperçu")
            return
            
        # Obtenir la taille du canvas
        self.concat_canvas.update_idletasks()
        canvas_width = self.concat_canvas.winfo_width()
        canvas_height = self.concat_canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            # Calculer le zoom optimal
            img_width, img_height = self.concat_result_image.size
            zoom_w = (canvas_width / img_width) * 100
            zoom_h = (canvas_height / img_height) * 100
            
            # Utiliser le plus petit zoom pour que tout rentre
            optimal_zoom = min(zoom_w, zoom_h, 100)
            
            self.concat_zoom_scale.set(int(optimal_zoom))
            self.display_concat_image()
            self.log(f"🔍 Zoom ajusté à {int(optimal_zoom)}%")
    
    def start_concat_pan(self, event):
        """Démarre le déplacement dans le canvas de concaténation"""
        self.concat_canvas.scan_mark(event.x, event.y)
    
    def pan_concat_image(self, event):
        """Déplace l'image dans le canvas de concaténation"""
        self.concat_canvas.scan_dragto(event.x, event.y, gain=1)
    
    def save_final_table(self):
        """Sauvegarde le tableau final"""
        if not self.panorama_files:
            messagebox.showwarning("Aucun panorama", "Veuillez charger des panoramas")
            return
            
        output_file = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        
        if not output_file:
            return
            
        use_concat = messagebox.askyesno("Méthode", "Utiliser concat.py?")
        
        if use_concat:
            folder = Path(list(self.panorama_files.values())[0]).parent
            cmd = [sys.executable, 'concat.py', str(folder)]
            try:
                subprocess.run(cmd, check=True)
                self.log("Tableau créé avec concat.py")
                messagebox.showinfo("Succès", "Tableau sauvegardé")
            except:
                messagebox.showerror("Erreur", "Erreur lors de la création")
        else:
            self.generate_final_table(output_file)
    
    def generate_final_table(self, output_file):
        """Génère directement le tableau (exclut 'semaine')"""
        images = []
        headers = []
        
        for day in self.days:  # Utilise self.days qui n'inclut PAS 'semaine'
            if day in self.panorama_files:
                img = Image.open(self.panorama_files[day])
                images.append(img)
                headers.append(day.capitalize())
                
        if not images:
            return
            
        max_height = max(img.height for img in images)
        total_width = sum(img.width for img in images)
        header_height = 50
        
        result = Image.new('RGBA', (total_width, max_height + header_height), (255, 255, 255, 255))
        
        header_img = Image.new('RGBA', (total_width, header_height), (240, 240, 240, 255))
        draw = ImageDraw.Draw(header_img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = None
            
        x_offset = 0
        for img, header in zip(images, headers):
            text_width = len(header) * 10
            x = x_offset + (img.width - text_width) // 2
            y = 13
            draw.text((x, y), header, fill='black', font=font)
            x_offset += img.width
            
        result.paste(header_img, (0, 0))
        
        x_offset = 0
        for img in images:
            result.paste(img, (x_offset, header_height))
            x_offset += img.width
            
        result.save(output_file)
        self.log(f"Tableau sauvegardé: {output_file}")
        if 'semaine' in self.panorama_files:
            self.log("ℹ️ Note: 'semaine.png' n'a pas été inclus dans le tableau final")
        messagebox.showinfo("Succès", "Tableau sauvegardé (sans semaine)")

def main():
    root = tk.Tk()
    app = LastWarGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()