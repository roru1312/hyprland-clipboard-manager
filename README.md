# Hyprland Python Clipboard Manager

Un gestor de portapapeles rápido y estético para Hyprland usando **Rofi**, **Cliphist** y **Python**.

Diseñado para solucionar los problemas de "glitches" visuales y corrupción de texto en listas largas, ofreciendo una interfaz compacta tipo IDE.

## ✨ Características
- **Detección Inteligente:** Distingue entre Comandos (Rojo), Imágenes (Violeta), URLs (Azul) y Texto.
- **Sin Artefactos:** Usa Python para escapar caracteres HTML y evitar errores visuales en Rofi.
- **Compacto:** Diseño optimizado para ocupar poco espacio visual.
- **Rápido:** Filtrado y renderizado instantáneo.

## 📦 Dependencias
Arch Linux / CachyOS:
```bash
sudo pacman -S python rofi-wayland cliphist wl-clipboard grim slurp
