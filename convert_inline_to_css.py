
import os
import re
import hashlib

# Dossier du repo
repo_path = "./"  # Exécuter depuis la racine du projet
css_file_path = os.path.join(repo_path, "style.css")

css_classes = {}
class_counter = 1

def generate_class_name(style):
    # Génère un nom unique basé sur le style
    hash_val = hashlib.md5(style.encode()).hexdigest()[:6]
    return f"auto-style-{hash_val}"

# Parcourir tous les fichiers HTML
for root, dirs, files in os.walk(repo_path):
    for filename in files:
        if filename.endswith(".html"):
            filepath = os.path.join(root, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Supprimer les blocs <style>...</style> et les stocker
            block_styles = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
            for style in block_styles:
                css_classes[f"block-{class_counter}"] = style.strip()
                class_counter += 1
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)

            # Remplacer les styles inline par des classes
            def replace_inline(match):
                style = match.group(1).strip()
                class_name = css_classes.get(style)
                if not class_name:
                    class_name = generate_class_name(style)
                    css_classes[style] = class_name
                return f'class="{class_name}"'

            content = re.sub(r'style="([^"]+)"', replace_inline, content)

            # Ajouter la balise <link> si absente
            if '<head>' in content and 'rel="stylesheet" href="style.css"' not in content:
                content = content.replace('<head>', '<head>\n<link.css')

            # Réécrire le fichier HTML
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

# Écrire les classes dans style.css
with open(css_file_path, "w", encoding="utf-8") as f:
    for style, class_name in css_classes.items():
        f.write(f".{class_name} {{ {style} }}\n")

print(f"✅ Terminé : classes générées et appliquées")
