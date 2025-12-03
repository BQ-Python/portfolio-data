
import os
import re

repo_path = "./"  # Racine du projet

for root, dirs, files in os.walk(repo_path):
    for filename in files:
        if filename.endswith(".html"):
            filepath = os.path.join(root, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Supprimer les lignes incorrectes (link.css, style.css isolé)
            content = re.sub(r'\\s*link\\.css\\s*', '', content)
            content = re.sub(r'\\s*style\\.css\\s*', '', content)

            # Ajouter la balise correcte si absente
            if '<head>' in content and 'rel="stylesheet" href="style.css"' not in content:
                content = content.replace('<head>', '<head>\nstyle.css')

            # Réécrire le fichier corrigé
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

print("✅ Correction terminée : balises <head> netto")
