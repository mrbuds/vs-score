#!/usr/bin/env python3
"""
Configuration centralisée pour Last War
Gère les paramètres par défaut et la persistance des préférences utilisateur
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict

@dataclass
class Config:
    """Configuration de l'application Last War"""
    
    # Jours de la semaine
    days: tuple = ('lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi')
    all_days: tuple = ('lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'semaine')
    
    # Capture vidéo
    default_fps: int = 30
    min_fps: int = 10
    max_fps: int = 60
    
    # Traitement parallèle
    max_workers: int = 3
    min_workers: int = 1
    max_workers_limit: int = 6
    process_timeout: int = 300  # 5 minutes
    
    # Panorama
    template_height: int = 100
    min_template_height: int = 50
    max_template_height: int = 200
    quality_threshold: float = 0.8
    min_quality: float = 0.5
    max_quality: float = 1.0
    min_scroll: int = 5
    duplicate_threshold: int = 5
    
    # Interface
    window_width: int = 1200
    window_height: int = 800
    zoom_min: int = 10
    zoom_max: int = 200
    zoom_default: int = 100
    zoom_step: int = 10
    
    # Édition
    crop_max: int = 20000
    crop_increment: int = 10
    header_height: int = 60
    header_font_size: int = 30
    
    # Chemins (non persistés)
    last_video_folder: str = ""
    last_panorama_folder: str = ""
    last_output_folder: str = ""
    
    # Fichier de config
    _config_file: Path = field(default_factory=lambda: Path.home() / '.lastwar_config.json')
    
    def save(self, path: Path = None):
        """Sauvegarde la configuration dans un fichier JSON"""
        if path is None:
            path = self._config_file
        
        try:
            # Convertir en dict (exclure les champs privés)
            data = {k: v for k, v in asdict(self).items() if not k.startswith('_')}
            
            # Convertir les tuples en listes pour JSON
            for key, value in data.items():
                if isinstance(value, tuple):
                    data[key] = list(value)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Erreur sauvegarde config: {e}")
            return False
    
    def load(self, path: Path = None):
        """Charge la configuration depuis un fichier JSON"""
        if path is None:
            path = self._config_file
        
        if not path.exists():
            return False
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Mettre à jour les attributs
            for key, value in data.items():
                if hasattr(self, key) and not key.startswith('_'):
                    # Convertir les listes en tuples pour days/all_days
                    if key in ('days', 'all_days') and isinstance(value, list):
                        value = tuple(value)
                    setattr(self, key, value)
            
            return True
        except Exception as e:
            print(f"Erreur chargement config: {e}")
            return False
    
    def reset(self):
        """Remet les valeurs par défaut"""
        default = Config()
        for key in asdict(default):
            if not key.startswith('_'):
                setattr(self, key, getattr(default, key))


# Instance globale
config = Config()

# Charger la config au démarrage si elle existe
config.load()
