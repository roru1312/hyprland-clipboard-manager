#!/usr/bin/env python3

import sys
import subprocess
import html
import re
import os

# --- PALETA (Tu estilo Kitty/Micro) ---
C = {
    "bg":     "#0a0a0af2", # Fondo casi negro
    "fg":     "#e0e0e0",   # Texto blanco suave
    "border": "#40a02b",   # Borde Verde
    "sel_bg": "#202020",   # Selección gris oscuro
    "sel_fg": "#ffffff",   # Texto seleccionado blanco
    "accent": "#ff3d2b",   # Rojo para comandos/código
    "img":    "#cba6f7",   # Violeta para imágenes
    "url":    "#1e66f5",   # Azul para links
    "env":    "#df8e1d",   # Amarillo para variables/ids
}

FONT = "JetBrainsMono Nerd Font 11" # Un punto menos para compactar
THEME_FILE = "/tmp/rofi_clip_compact.rasi"

# --- GENERACIÓN DE TEMA COMPACTO ---
def generate_theme():
    css = f"""
    * {{
        background-color: transparent;
        text-color:       {C['fg']};
        font:             "{FONT}";
    }}
    window {{
        background-color: {C['bg']};
        border:           2px;
        border-color:     {C['border']};
        border-radius:    4px;
        width:            900px;
        padding:          10px; /* Reducido de 20px a 10px (Más compacto) */
    }}
    mainbox {{ spacing: 5px; }} /* Menos espacio entre barra y lista */
    inputbar {{
        children: [ prompt, entry ];
        margin:   0 0 5px 0;
        text-color: {C['border']};
    }}
    prompt {{
        font: "JetBrainsMono Nerd Font Bold 11";
        margin: 0 10px 0 0;
        text-color: {C['border']};
    }}
    entry {{ placeholder: "Escribe para filtrar..."; placeholder-color: #666; }}

    listview {{
        lines: 12;
        spacing: 2px; /* Elementos más juntos */
        scrollbar: true;
        scrollbar-width: 4px;
        fixed-height: false;
    }}
    element {{
        padding: 4px 8px; /* Elementos más finos verticalmente */
        border-radius: 3px;
    }}
    element selected {{
        background-color: {C['sel_bg']};
        text-color:       {C['sel_fg']};
        border:           1px;
        border-color:     {C['border']};
    }}
    /* Renderizar colores Pango en la lista */
    element-text {{
        highlight: bold #a6e3a1;
        vertical-align: 0.5;
    }}
    """
    with open(THEME_FILE, "w") as f: f.write(css)

# --- LÓGICA DE DETECCIÓN INTELIGENTE ---
def format_line(line):
    """
    Analiza la línea cruda de cliphist y le aplica formato visual
    PARA LA LISTA PRINCIPAL.
    """
    # Separar ID del contenido (cliphist devuelve: "123 <tab> contenido...")
    parts = line.split("\t", 1)
    if len(parts) < 2: return line
    clip_id, text = parts[0], parts[1].strip()

    # Escapamos el texto base para evitar romper Pango
    safe_text = html.escape(text.replace("\n", " ↵ "))

    # 1. DETECCIÓN DE IMAGEN
    if "[[ binary data" in text:
        # Extraemos info básica si existe (ej: png 500x500)
        meta = text.replace("[[ binary data", "").replace("]]", "").strip()
        # Reemplazamos el texto feo por algo bonito
        display = f"<span color='{C['img']}'><b>  IMAGEN</b></span> <span size='small' color='#888'>({meta})</span>"
        return f"{clip_id}\t{display}\0icon\x1fimage-x-generic" # Intenta poner icono genérico

    # 2. DETECCIÓN DE CÓDIGO / COMANDOS (Rojo)
    # Palabras clave comunes
    if re.search(r'^\s*(sudo|git|pacman|yay|docker|npm|pip|ssh|cd|ls|mkdir|chmod|python|import|def|class|const|var|let|function|#!)', text):
        display = f"<span color='{C['accent']}'><b>  CMD</b></span>  {safe_text}"
        return f"{clip_id}\t{display}"

    # 3. DETECCIÓN DE ENV VARS / CRYPTO (Amarillo)
    # Ej: API_KEY=..., 0x..., direcciones largas
    if re.match(r'^[A-Z0-9_]+=', text) or re.search(r'\b0x[a-fA-F0-9]{10,}\b', text) or re.search(r'\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b', text):
        display = f"<span color='{C['env']}'><b>  KEY</b></span>  {safe_text}"
        return f"{clip_id}\t{display}"

    # 4. DETECCIÓN DE URLS / MAILS (Azul)
    if re.search(r'(https?://|@)', text):
        display = f"<span color='{C['url']}'><b>  LINK</b></span> {safe_text}"
        return f"{clip_id}\t{display}"

    # 5. TEXTO PLANO (Normal)
    return f"{clip_id}\t<span color='#888'> </span> {safe_text}"

def rofi_menu(formatted_lines):
    # Unimos las líneas formateadas
    input_str = "\n".join(formatted_lines)

    cmd = [
        "rofi", "-dmenu",
        "-theme", THEME_FILE,
        "-p", "❯ Portapapeles",
        "-markup-rows",       # CRUCIAL: Permite los colores en la lista
        "-format", "i s",     # Devuelve índice y texto seleccionado
        "-kb-custom-1", "Alt+Left",
        "-kb-custom-2", "Alt+Right"
    ]

    try:
        proc = subprocess.run(cmd, input=input_str, capture_output=True, text=True)
        return proc.returncode, proc.stdout.strip()
    except Exception:
        return 1, ""

def main():
    generate_theme()

    # 1. Obtener historial crudo
    try:
        raw_output = subprocess.check_output(["cliphist", "list"], text=True).strip()
    except:
        sys.exit(1)

    if not raw_output: sys.exit()

    lines = raw_output.splitlines()

    # 2. Procesar líneas (Aplicar iconos y colores)
    formatted_data = [format_line(l) for l in lines]

    while True:
        # 3. Mostrar Rofi
        code, result = rofi_menu(formatted_data)

        if code == 1: sys.exit(0) # Esc

        # Parsear resultado (Rofi devuelve "Indice TextoSeleccionado")
        # Necesitamos el ID original para cliphist
        if not result: continue

        try:
            # cliphist espera "ID <espacio> Texto..."
            # Pero como modificamos el texto visualmente, necesitamos recuperar el ID real.
            # Rofi con -format 'i s' nos da el índice de la línea original.

            # El output de rofi es algo como "0 125    <span>...</span>"
            # Pero cuidado, rofi devuelve el indice de la lista FILTRADA si usas filtro.
            # Estrategia más segura: El ID sigue estando al principio de la string visual "\t"

            # Extraer la línea seleccionada (la parte de texto)
            selection_text = result.split(" ", 1)[1] if " " in result else ""

            # El ID es lo que está antes del primer tabulador
            clip_id = selection_text.split("\t")[0]

        except IndexError:
            continue

        # ACCIONES
        if code == 0: # ENTER -> Copiar
            # Usamos cliphist decode con el ID
            subprocess.run(f"cliphist decode {clip_id} | wl-copy", shell=True)
            sys.exit(0)

        elif code == 11: # Alt+Der -> Borrar
            subprocess.run(f"cliphist delete {clip_id}", shell=True)
            # Recargar script (opcional, o salir)
            sys.exit(0)

        elif code == 10: # Alt+Izq -> PREVIEW SIMPLE
            # Decodificamos el contenido real
            try:
                content = subprocess.check_output(f"cliphist decode {clip_id}", shell=True)
                # Intentamos detectar si es binario (imagen) mirando los primeros bytes
                # O simplemente ver si falla decodificar utf-8
                try:
                    text_content = content.decode('utf-8')
                    # Es texto -> Mostramos texto plano
                    view_str = html.escape(text_content)
                    msg = "Texto Plano (Sin formato)"
                except UnicodeDecodeError:
                    # Es binario -> Probablemente imagen
                    view_str = "🖼️\n\nEste elemento es una imagen o dato binario.\nPresiona Enter para copiarlo."
                    msg = "Vista Previa de Imagen"

            except:
                view_str = "Error al leer contenido."
                msg = "Error"

            # Mostrar Visor SIMPLE (Sin colores locos para evitar artifacts)
            # Usamos el mismo tema
            subprocess.run([
                "rofi", "-e", view_str,
                "-theme", THEME_FILE,
                "-theme-str", 'window { width: 800px; }',
                "-theme-str", f'message {{ padding: 20px; font: "{FONT}"; }}'
            ])
            # Al cerrar el visor (Enter/Esc), el bucle while vuelve a mostrar la lista principal

if __name__ == "__main__":
    main()
