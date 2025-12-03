# fix_all_html.py
import os
import re

REPO_PATH = "./"  # Change si besoin (ex: "C:/mon-site")

# Les deux balises qu’on veut avoir dans TOUS les HTML
CSS_LINK = '<link rel="stylesheet" href="style.css">'
FONT_LINK = '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">'

def fix_head(html_content):
    # 1. Nettoyer tout ce qui ressemble à un lien cassé vers style.css ou Google Fonts
    content = re.sub(r'<link[^>]*style\.css[^>]*>', '', html_content, flags=re.IGNORECASE)
    content = re.sub(r'<link[^>]*fonts\.googleapis\.com[^>]*>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\d\?family=Inter[^"]*', '', content)  # nettoie les bouts cassés du type "2?family=Inter..."

    # 2. Trouver la balise <head ...>
    head_match = re.search(r'(<head\b[^>]*>)', content, flags=re.IGNORECASE)
    if not head_match:
        return content, False  # pas de <head> → on touche pas (rare)

    head_tag = head_match.group(1)
    start = head_match.end()

    # Extraire tout ce qui est déjà dans <head> jusqu'à </head>
    body_start = content.find('</head>', start)
    if body_start == -1:
        body_start = len(content)

    inside_head = content[start:body_start]

    # 3. Construire un <head> propre
    new_inside = f"""
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Horizon Labs - Articles & Rapports</title>
    
    {FONT_LINK}
    {CSS_LINK}
"""

    # Garder le <title> existant (plus robuste)
    title_match = re.search(r'<title>(.*?)</title>', inside_head, flags=re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Horizon Labs"

    new_inside = f"""
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    
    {FONT_LINK}
    {CSS_LINK}
"""

    # 4. Remplacer le contenu du <head>
    new_head_content = head_tag + new_inside + "\n</head>"
    new_content = content[:head_match.start()] + new_head_content + content[body_start + 7:]

    modified = new_content != html_content
    return new_content, modified

def main():
    count_fixed = 0
    count_total = 0

    for root, dirs, files in os.walk(REPO_PATH):
        for file in files:
            if file.endswith(".html"):
                path = os.path.join(root, file)
                count_total += 1

                with open(path, "r", encoding="utf-8") as f:
                    original = f.read()

                new_content, modified = fix_head(original)

                if modified:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"CORRIGÉ → {path}")
                    count_fixed += 1
                else:
                    print(f"Déjà bon → {path}")

    print("\n" + "="*50)
    print(f"Terminé ! {count_fixed}/{count_total} fichiers corrigés.")
    print("="*50)

if __name__ == "__main__":
    main()