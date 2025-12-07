#!/usr/bin/env python3
"""
Module de génération de tableaux
Factorisation du code commun entre concat.py et main.py
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import re

from config import config


class TableGenerator:
    """Génère des tableaux combinés à partir de panoramas"""
    
    @staticmethod
    def parse_folder_dates(folder_name):
        """
        Extrait les dates de début et fin depuis le nom du dossier.
        Format attendu: 'sXwY dd-mm dd-mm'
        
        Returns:
            datetime ou None si parsing échoue
        """
        pattern = r'(\d{2})-(\d{2})\s+(\d{2})-(\d{2})$'
        match = re.search(pattern, folder_name)
        if not match:
            return None
        
        try:
            start_day, start_month, end_day, end_month = map(int, match.groups())
            current_year = datetime.now().year
            
            start_date = datetime(current_year, start_month, start_day)
            end_date = datetime(current_year, end_month, end_day)
            
            # Vérifier que c'est bien 6 jours (lundi à samedi)
            if (end_date - start_date) != timedelta(days=5):
                return None
            
            return start_date
        except ValueError:
            return None
    
    @staticmethod
    def generate_headers(start_date=None, days_found=None):
        """
        Génère les en-têtes des colonnes.
        
        Args:
            start_date: Date de début (pour ajouter les dates)
            days_found: Liste des jours trouvés (pour filtrer)
        
        Returns:
            Liste des en-têtes
        """
        days_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
        days_map = {d.lower(): d for d in days_fr}
        
        if start_date:
            # Avec dates
            headers = []
            current_date = start_date
            for day in days_fr:
                if days_found is None or day.lower() in days_found:
                    headers.append(f"{day} {current_date.strftime('%d/%m')}")
                current_date += timedelta(days=1)
            return headers
        else:
            # Sans dates
            if days_found:
                return [days_map.get(d, d.capitalize()) for d in days_found]
            return days_fr
    
    @staticmethod
    def load_font(size=None):
        """Charge une police appropriée"""
        if size is None:
            size = config.header_font_size
        
        # Essayer plusieurs polices
        font_candidates = [
            "arial.ttf",
            "Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        
        for font_path in font_candidates:
            try:
                return ImageFont.truetype(font_path, size)
            except (OSError, IOError):
                continue
        
        # Fallback
        return ImageFont.load_default()
    
    @staticmethod
    def generate(images, headers, output_path, header_height=None, transparent_bg=False):
        """
        Génère un tableau combiné à partir d'images.
        
        Args:
            images: Liste d'objets PIL.Image
            headers: Liste des en-têtes (même longueur que images)
            output_path: Chemin de sortie (Path ou str)
            header_height: Hauteur de l'en-tête (défaut: config.header_height)
            transparent_bg: Si True, fond transparent
        
        Returns:
            Tuple (success: bool, result_image: Image ou None, error: str ou None)
        """
        if not images:
            return False, None, "Aucune image fournie"
        
        if len(images) != len(headers):
            return False, None, f"Nombre d'images ({len(images)}) != nombre d'en-têtes ({len(headers)})"
        
        if header_height is None:
            header_height = config.header_height
        
        try:
            # Calculer les dimensions
            max_height = max(img.height for img in images)
            total_width = sum(img.width for img in images)
            total_height = max_height + header_height
            
            # Créer l'image résultat
            bg_color = (255, 255, 255, 0) if transparent_bg else (255, 255, 255, 255)
            result = Image.new('RGBA', (total_width, total_height), bg_color)
            
            # Créer l'en-tête
            header_bg = (240, 240, 240, 255) if not transparent_bg else (255, 255, 255, 255)
            header_img = Image.new('RGBA', (total_width, header_height), header_bg)
            draw = ImageDraw.Draw(header_img)
            
            # Charger la police
            font = TableGenerator.load_font()
            
            # Dessiner les en-têtes
            x_offset = 0
            for img, header in zip(images, headers):
                # Centrer le texte
                bbox = draw.textbbox((0, 0), header, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                x = x_offset + (img.width - text_width) // 2
                y = (header_height - text_height) // 2
                
                draw.text((x, y), header, fill=(0, 0, 0, 255), font=font)
                x_offset += img.width
            
            # Coller l'en-tête
            result.paste(header_img, (0, 0))
            
            # Coller les images
            x_offset = 0
            for img in images:
                # Convertir en RGBA si nécessaire
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                result.paste(img, (x_offset, header_height))
                x_offset += img.width
            
            # Sauvegarder
            output_path = Path(output_path)
            result.save(output_path)
            
            return True, result, None
            
        except Exception as e:
            return False, None, str(e)
    
    @staticmethod
    def generate_from_folder(folder_path, output_name=None, days=None):
        """
        Génère un tableau à partir d'un dossier contenant les panoramas.
        
        Args:
            folder_path: Chemin du dossier
            output_name: Nom du fichier de sortie (défaut: nom du dossier)
            days: Liste des jours à inclure (défaut: lundi à samedi)
        
        Returns:
            Tuple (success: bool, output_path: Path ou None, error: str ou None)
        """
        folder_path = Path(folder_path)
        
        if not folder_path.is_dir():
            return False, None, f"Dossier invalide: {folder_path}"
        
        if days is None:
            days = list(config.days)  # Exclure 'semaine'
        
        # Charger les images
        images = []
        valid_days = []
        
        for day in days:
            img_path = folder_path / f"{day}.png"
            if img_path.exists():
                try:
                    img = Image.open(img_path)
                    images.append(img)
                    valid_days.append(day)
                except Exception as e:
                    print(f"Erreur chargement {img_path}: {e}")
        
        if not images:
            return False, None, "Aucune image trouvée dans le dossier"
        
        # Générer les en-têtes
        folder_name = folder_path.name
        start_date = TableGenerator.parse_folder_dates(folder_name)
        headers = TableGenerator.generate_headers(start_date, valid_days)
        
        # Nom de sortie
        if output_name is None:
            output_name = f"{folder_name}.png"
        
        output_path = folder_path / output_name
        
        # Générer le tableau
        success, result, error = TableGenerator.generate(
            images, headers, output_path, transparent_bg=True
        )
        
        # Fermer les images
        for img in images:
            img.close()
        
        if success:
            return True, output_path, None
        else:
            return False, None, error
