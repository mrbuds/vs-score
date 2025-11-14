#!/usr/bin/env python3
"""
Interface Last War - Fichier principal
Version améliorée: onglet 3 simplifié, pas de popups de confirmation
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageTk
from datetime import datetime
import subprocess
import sys
import queue
import re

# Importer les modules
from video_processor import VideoProcessor
from panorama_editor import PanoramaEditor
from video_capture import VideoCapture

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
        self.current_capture_output = None
        
        # Configuration
        self.days = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi']
        self.all_days = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'semaine']
        
        # Modules
        self.video_processor = VideoProcessor(self)
        self.panorama_editor = PanoramaEditor(self)
        self.video_capture = VideoCapture(self)
        
        self.setup_ui()
        self.check_update_queue()
        
    def setup_ui(self):
        """Crée l'interface utilisateur"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.capture_tab = ttk.Frame(notebook)
        notebook.add(self.capture_tab, text="0. Capturer vidéos")
        self.setup_capture_tab()
        
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
    
    def setup_capture_tab(self):
        """Onglet 0 - Capture vidéo"""
        # Frame principal
        main_frame = ttk.Frame(self.capture_tab)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # === INFO ===
        info_frame = ttk.LabelFrame(main_frame, text="ℹ️ Comment ça marche")
        info_frame.pack(fill='x', pady=5)
        
        info_text = """1. Configurez le nom du fichier et le dossier de sortie ci-dessous
2. Cliquez sur 'Ouvrir l'overlay de capture'
3. Tracez un cadre avec la souris (il restera visible)
4. Utilisez les boutons flottants sous le cadre pour contrôler l'enregistrement"""
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT, font=('Arial', 9)).pack(padx=10, pady=10)
        
        # === DOSSIER DE SORTIE ===
        folder_frame = ttk.LabelFrame(main_frame, text="📁 Dossier de sortie")
        folder_frame.pack(fill='x', pady=5)
        
        folder_inner = ttk.Frame(folder_frame)
        folder_inner.pack(fill='x', padx=10, pady=10)
        
        self.output_folder_var = tk.StringVar(value=str(Path.cwd()))
        ttk.Entry(folder_inner, textvariable=self.output_folder_var, state='readonly').pack(side=tk.LEFT, fill='x', expand=True, padx=(0, 5))
        ttk.Button(folder_inner, text="Parcourir...", command=self.select_output_folder).pack(side=tk.LEFT)
        
        # === NOM DU FICHIER ===
        naming_frame = ttk.LabelFrame(main_frame, text="📝 Nom du fichier")
        naming_frame.pack(fill='x', pady=5)
        
        naming_inner = ttk.Frame(naming_frame)
        naming_inner.pack(fill='x', padx=10, pady=10)
        
        # Type de nommage
        self.naming_mode = tk.StringVar(value="preset")
        
        preset_radio = ttk.Radiobutton(naming_inner, text="Jour prédéfini:", 
                                       variable=self.naming_mode, value="preset",
                                       command=self.update_naming_mode)
        preset_radio.grid(row=0, column=0, sticky='w', pady=5)
        
        self.day_combo_capture = ttk.Combobox(naming_inner, values=self.all_days, 
                                               state='readonly', width=15)
        self.day_combo_capture.current(0)
        self.day_combo_capture.grid(row=0, column=1, padx=10, pady=5)
        
        custom_radio = ttk.Radiobutton(naming_inner, text="Nom personnalisé:", 
                                       variable=self.naming_mode, value="custom",
                                       command=self.update_naming_mode)
        custom_radio.grid(row=1, column=0, sticky='w', pady=5)
        
        self.custom_name_entry = ttk.Entry(naming_inner, width=30)
        self.custom_name_entry.grid(row=1, column=1, padx=10, pady=5, sticky='ew')
        self.custom_name_entry.insert(0, "capture")
        self.custom_name_entry.config(state='disabled')
        
        ttk.Label(naming_inner, text=".mp4").grid(row=1, column=2)
        
        naming_inner.columnconfigure(1, weight=1)
        
        # Aperçu du nom
        self.filename_preview = ttk.Label(naming_frame, text="📄 Fichier: lundi.mp4", 
                                          foreground="blue")
        self.filename_preview.pack(pady=5)
        
        # === RÉGLAGES ===
        settings_frame = ttk.LabelFrame(main_frame, text="⚙️ Réglages")
        settings_frame.pack(fill='x', pady=5)
        
        settings_inner = ttk.Frame(settings_frame)
        settings_inner.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(settings_inner, text="FPS:").pack(side=tk.LEFT, padx=5)
        self.fps_var = tk.IntVar(value=30)
        fps_spinner = ttk.Spinbox(settings_inner, from_=10, to=60, textvariable=self.fps_var, 
                                   width=10, command=self.update_fps)
        fps_spinner.pack(side=tk.LEFT, padx=5)
        
        # === BOUTON PRINCIPAL ===
        control_frame = ttk.LabelFrame(main_frame, text="🎬 Lancer la capture")
        control_frame.pack(fill='x', pady=5)
        
        info_text = """Cliquez sur le bouton ci-dessous pour ouvrir l'overlay de capture.

Vous pourrez alors :
1. Tracer le cadre de capture avec la souris
2. Utiliser les boutons flottants pour démarrer/arrêter/annuler"""
        
        ttk.Label(control_frame, text=info_text, justify=tk.LEFT, foreground="gray").pack(pady=10)
        
        self.capture_button = tk.Button(
            control_frame, text="🎯 Ouvrir l'overlay de capture", 
            command=self.open_capture_overlay,
            bg='#4CAF50', fg='white', font=('Arial', 12, 'bold'),
            padx=30, pady=15, cursor='hand2'
        )
        self.capture_button.pack(pady=10)
        
        # === CONSEILS ===
        tips_frame = ttk.LabelFrame(main_frame, text="💡 Conseils")
        tips_frame.pack(fill='x', pady=5)
        
        tips_text = """1. Sélectionnez d'abord la zone à capturer
2. Choisissez le nom du fichier (jour ou personnalisé)
3. Cliquez sur 'Démarrer l'enregistrement'
4. Dans le jeu, scrollez de haut en bas
5. Cliquez sur 'Arrêter et sauvegarder'"""
        
        ttk.Label(tips_frame, text=tips_text, justify=tk.LEFT, font=('Arial', 9)).pack(padx=10, pady=10)
        
        # Mettre à jour les callbacks
        self.day_combo_capture.bind('<<ComboboxSelected>>', lambda e: self.update_filename_preview())
        self.custom_name_entry.bind('<KeyRelease>', lambda e: self.update_filename_preview())
        
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
        
        # Boutons d'action
        ttk.Button(crop_frame, text="⬇️ Aller en bas", command=self.panorama_editor.scroll_to_bottom).grid(row=2, column=0, pady=3)
        ttk.Button(crop_frame, text="⬆️ Aller en haut", command=self.panorama_editor.scroll_to_top).grid(row=2, column=1, pady=3)
        ttk.Button(crop_frame, text="📏 Ajuster à la fenêtre", command=self.panorama_editor.fit_to_window).grid(row=3, column=0, columnspan=2, pady=3)
        
        # Zoom
        zoom_frame = ttk.LabelFrame(control_panel, text="Zoom")
        zoom_frame.pack(fill='x', pady=10)
        
        self.zoom_scale = tk.Scale(zoom_frame, from_=10, to=200, orient=tk.HORIZONTAL, label="%", command=self.set_zoom)
        self.zoom_scale.set(100)
        self.zoom_scale.pack(fill='x', padx=5, pady=5)
        
        # Actions - SANS POPUPS
        action_frame = ttk.LabelFrame(control_panel, text="Actions")
        action_frame.pack(fill='x', pady=10)
        
        ttk.Button(action_frame, text="✂️ Appliquer recadrage", command=self.panorama_editor.apply_crop).pack(fill='x', padx=5, pady=5)
        ttk.Button(action_frame, text="↩️ Annuler", command=self.panorama_editor.undo_changes).pack(fill='x', padx=5, pady=5)
        ttk.Button(action_frame, text="💾 Sauvegarder", command=self.panorama_editor.save_edited_panorama).pack(fill='x', padx=5, pady=5)
        
        self.info_label = ttk.Label(control_panel, text="Aucune image chargée", wraplength=200)
        self.info_label.pack(pady=10)
        
        # Bindings
        self.edit_canvas.bind("<Button-3>", self.panorama_editor.set_crop_line)
        self.edit_canvas.bind("<MouseWheel>", self.panorama_editor.zoom_image)
        self.edit_canvas.bind("<Button-1>", self.panorama_editor.start_pan)
        self.edit_canvas.bind("<B1-Motion>", self.panorama_editor.pan_image)
        
    def setup_concat_tab(self):
        """Onglet 3 - Tableau final (SIMPLIFIÉ)"""
        # Frame principal
        main_frame = ttk.Frame(self.concat_tab)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Info
        info_frame = ttk.LabelFrame(main_frame, text="📊 Génération du tableau final")
        info_frame.pack(fill='both', expand=True, pady=10)
        
        info_text = """
Cette fonction combine automatiquement tous les panoramas de la semaine
(Lundi à Samedi) en un seul grand tableau.

Le fichier sera sauvegardé dans le même dossier que vos panoramas
avec le nom du dossier parent.

Note: Le fichier 'semaine.png' ne sera PAS inclus dans le tableau final.
        """
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT, font=('Arial', 10)).pack(padx=20, pady=20)
        
        # Status
        self.concat_status = ttk.Label(info_frame, text="", foreground="blue", font=('Arial', 10, 'bold'))
        self.concat_status.pack(pady=10)
        
        # Bouton principal - GROS et visible
        button_frame = ttk.Frame(info_frame)
        button_frame.pack(pady=30)
        
        generate_btn = tk.Button(button_frame, 
                                 text="🎨 Générer le tableau final", 
                                 command=self.generate_and_save_final_table,
                                 font=('Arial', 14, 'bold'),
                                 bg='#4CAF50',
                                 fg='white',
                                 padx=30,
                                 pady=15,
                                 cursor='hand2')
        generate_btn.pack()
        
        # Conseils
        tips_frame = ttk.LabelFrame(main_frame, text="💡 Conseils")
        tips_frame.pack(fill='x', pady=10)
        
        tips_text = """
• Assurez-vous d'avoir chargé les panoramas dans l'onglet 2
• Les jours manquants seront automatiquement ignorés
• Le tableau est sauvegardé automatiquement sans confirmation
        """
        
        ttk.Label(tips_frame, text=tips_text, justify=tk.LEFT, font=('Arial', 9)).pack(padx=20, pady=10)
    
    def generate_and_save_final_table(self):
        """Génère et sauvegarde automatiquement le tableau final - SIMPLIFIÉ"""
        if not self.panorama_files:
            messagebox.showwarning("Aucun panorama", "Veuillez d'abord charger des panoramas dans l'onglet 2")
            return
        
        self.concat_status.config(text="⏳ Génération en cours...", foreground="orange")
        self.root.update()
        
        try:
            # Déterminer le dossier de sortie
            first_panorama = list(self.panorama_files.values())[0]
            folder = Path(first_panorama).parent
            folder_name = folder.name
            
            # Nom du fichier de sortie basé sur le dossier
            output_file = folder / f"{folder_name}.png"
            
            # Collecter les images (sans 'semaine')
            images = []
            headers = []
            days_found = []
            
            for day in self.days:  # Uniquement lundi à samedi
                if day in self.panorama_files:
                    img_path = self.panorama_files[day]
                    if img_path.exists():
                        img = Image.open(img_path)
                        images.append(img)
                        headers.append(day.capitalize())
                        days_found.append(day)
            
            if not images:
                self.concat_status.config(text="❌ Aucune image trouvée", foreground="red")
                messagebox.showerror("Erreur", "Aucun panorama trouvé pour générer le tableau")
                return
            
            self.log(f"📊 Génération du tableau avec {len(images)} jour(s): {', '.join(days_found)}")
            
            # Calculer les dimensions
            max_height = max(img.height for img in images)
            total_width = sum(img.width for img in images)
            header_height = 60
            
            # Créer l'image résultat
            result = Image.new('RGBA', (total_width, max_height + header_height), (255, 255, 255, 255))
            
            # Créer l'en-tête
            header_img = Image.new('RGBA', (total_width, header_height), (240, 240, 240, 255))
            draw = ImageDraw.Draw(header_img)
            
            # Charger une police
            try:
                font = ImageFont.truetype("arial.ttf", 30)
            except:
                try:
                    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
                except:
                    font = ImageFont.load_default()
            
            # Dessiner les en-têtes
            x_offset = 0
            for img, header in zip(images, headers):
                # Centrer le texte
                bbox = draw.textbbox((0, 0), header, font=font)
                text_width = bbox[2] - bbox[0]
                x = x_offset + (img.width - text_width) // 2
                y = (header_height - 30) // 2
                
                draw.text((x, y), header, fill=(0, 0, 0, 255), font=font)
                x_offset += img.width
            
            # Coller l'en-tête
            result.paste(header_img, (0, 0))
            
            # Coller les images
            x_offset = 0
            for img in images:
                result.paste(img, (x_offset, header_height))
                x_offset += img.width
            
            # Sauvegarder
            result.save(output_file)
            
            self.log(f"✅ Tableau sauvegardé: {output_file}")
            self.log(f"   Dimensions: {total_width}x{max_height + header_height}px")
            
            if 'semaine' in self.panorama_files:
                self.log("ℹ️  Note: 'semaine.png' n'a pas été inclus (utilisation séparée)")
            
            self.concat_status.config(text=f"✅ Tableau sauvegardé: {output_file.name}", foreground="green")
            
            # Afficher un message de succès discret
            self.root.after(100, lambda: messagebox.showinfo("Succès", 
                f"Tableau généré avec succès!\n\nFichier: {output_file.name}\nJours: {', '.join(days_found)}\nDimensions: {total_width}x{max_height}px"))
            
        except Exception as e:
            self.log(f"❌ Erreur lors de la génération: {e}")
            self.concat_status.config(text=f"❌ Erreur: {str(e)}", foreground="red")
            messagebox.showerror("Erreur", f"Impossible de générer le tableau:\n{e}")
    
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
        files = filedialog.askopenfilenames(
            title="Sélectionner les vidéos", 
            filetypes=[("Vidéos", "*.mp4 *.avi *.mov *.mkv"), ("Tous", "*.*")]
        )
        
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
        # Vérifier 'semaine' en premier
        if 'semaine' in filename_lower:
            return 'semaine'
        # Puis les autres jours
        for day in self.days:
            if day in filename_lower:
                return day
        return None
    
    def ask_day_for_file(self, filename):
        """Demande le jour pour un fichier"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Sélection du jour")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
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
    
    def refresh_panorama_list(self):
        """Rafraîchit la liste des panoramas disponibles dans l'onglet 2"""
        available_days = list(self.panorama_files.keys())
        self.day_combo['values'] = available_days
        if available_days and not self.day_combo.get():
            self.day_combo.current(0)
            # Charger automatiquement le panorama sélectionné
            self.load_panorama_for_edit()
        if available_days:
            self.log(f"🔄 Onglet 2 mis à jour: {len(available_days)} panorama(s) disponible(s) ({', '.join(available_days)})")
    
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
                
        self.refresh_panorama_list()
    
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
        
        # Ajouter les lignes de coupe
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
    
    # ===== MÉTHODES POUR L'ONGLET CAPTURE =====
    
    def select_output_folder(self):
        """Sélectionne le dossier de sortie pour les captures"""
        folder = filedialog.askdirectory(title="Sélectionner le dossier de sortie")
        if folder:
            self.output_folder_var.set(folder)
            self.video_capture.set_output_folder(folder)
            self.update_filename_preview()
    
    def update_naming_mode(self):
        """Met à jour le mode de nommage (preset/custom)"""
        if self.naming_mode.get() == "preset":
            self.day_combo_capture.config(state='readonly')
            self.custom_name_entry.config(state='disabled')
        else:
            self.day_combo_capture.config(state='disabled')
            self.custom_name_entry.config(state='normal')
        self.update_filename_preview()
    
    def update_filename_preview(self):
        """Met à jour l'aperçu du nom de fichier"""
        if self.naming_mode.get() == "preset":
            filename = f"{self.day_combo_capture.get()}.mp4"
        else:
            custom = self.custom_name_entry.get().strip()
            if not custom:
                custom = "capture"
            # Nettoyer le nom (enlever caractères invalides)
            import re
            custom = re.sub(r'[<>:"/\\|?*]', '', custom)
            filename = f"{custom}.mp4"
        
        folder = self.output_folder_var.get()
        full_path = Path(folder) / filename
        self.filename_preview.config(text=f"📄 Fichier: {filename}\n📁 {full_path}")
    
    def update_fps(self):
        """Met à jour le FPS de capture"""
        self.video_capture.set_fps(self.fps_var.get())
    
    def open_capture_overlay(self):
        """Ouvre l'overlay de capture avec cadre et boutons flottants"""
        # Obtenir le nom du fichier
        if self.naming_mode.get() == "preset":
            filename = f"{self.day_combo_capture.get()}.mp4"
        else:
            custom = self.custom_name_entry.get().strip()
            if not custom:
                messagebox.showwarning("Nom vide", "Veuillez entrer un nom de fichier")
                return
            import re
            custom = re.sub(r'[<>:"/\\|?*]', '', custom)
            filename = f"{custom}.mp4"
        
        output_path = Path(self.output_folder_var.get()) / filename
        
        # Vérifier si le fichier existe
        if output_path.exists():
            result = messagebox.askyesno("Fichier existant", 
                                         f"Le fichier {filename} existe déjà.\nVoulez-vous le remplacer?")
            if not result:
                return
        
        # Sauvegarder le chemin de sortie
        self.current_capture_output = output_path
        
        # Ouvrir l'overlay
        self.video_capture.select_region()
        self.log(f"📐 Overlay de capture ouvert pour: {filename}")
    
    def on_capture_start(self, region):
        """Callback quand la capture démarre depuis l'overlay"""
        self.log(f"📐 Zone sélectionnée: {region[2]}x{region[3]} à ({region[0]}, {region[1]})")
        
        # Démarrer l'enregistrement
        if self.video_capture.start_recording(self.current_capture_output):
            self.log(f"🔴 Enregistrement en cours: {self.current_capture_output.name}")
        else:
            self.log(f"❌ Impossible de démarrer l'enregistrement")
    
    def on_capture_stop(self):
        """Callback quand la capture s'arrête depuis l'overlay"""
        self.log(f"⏹️ Enregistrement arrêté et sauvegardé")
        
        # Ajouter la vidéo à l'onglet 1 si c'est un jour
        if self.naming_mode.get() == "preset":
            day = self.day_combo_capture.get()
            if day in self.all_days and self.current_capture_output.exists():
                self.video_files[day] = self.current_capture_output
                # Ajouter à la liste si pas déjà présent
                already_in_list = False
                for item in self.video_tree.get_children():
                    if self.video_tree.item(item)['values'][0] == day:
                        already_in_list = True
                        break
                if not already_in_list:
                    self.video_tree.insert('', 'end', values=(day, self.current_capture_output.name, "En attente", ""))
                self.log(f"📹 Vidéo ajoutée à l'onglet 1: {day}")
    
    def on_capture_cancel(self):
        """Callback quand la capture est annulée depuis l'overlay"""
        self.log(f"❌ Capture annulée")

def main():
    root = tk.Tk()
    app = LastWarGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()