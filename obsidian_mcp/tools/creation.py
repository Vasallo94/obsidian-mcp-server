"""
Herramientas de creación y edición para el vault de Obsidian
Incluye funciones para crear y modificar notas
"""

from datetime import datetime

from fastmcp import FastMCP

from ..config import get_vault_path
from ..utils import find_note_by_name, sanitize_filename


def register_creation_tools(mcp: FastMCP) -> None:
    """
    Registra todas las herramientas de creación en el servidor MCP
    
    Args:
        mcp: Instancia del servidor FastMCP
    """
    
    @mcp.tool()
    def crear_nota(titulo: str, contenido: str, carpeta: str = "", etiquetas: str = "") -> str:
        """
        Crea una nueva nota en el vault
        
        Args:
            titulo: Título de la nota (se usará como nombre de archivo)
            contenido: Contenido de la nota en Markdown
            carpeta: Carpeta donde crear la nota (vacío = raíz)
            etiquetas: Etiquetas separadas por comas (ej: "idea,reflexion,personal")
        """
        try:
            vault_path = get_vault_path()
            
            # Preparar nombre de archivo
            nombre_archivo = sanitize_filename(titulo)
            
            # Determinar ruta
            if carpeta:
                carpeta_path = vault_path / carpeta
                carpeta_path.mkdir(parents=True, exist_ok=True)
                nota_path = carpeta_path / nombre_archivo
            else:
                nota_path = vault_path / nombre_archivo
            
            # Verificar si ya existe
            if nota_path.exists():
                return f"❌ Ya existe una nota con el nombre '{nombre_archivo}'"
            
            # Preparar contenido con metadatos
            contenido_completo = ""
            
            # Agregar frontmatter si hay etiquetas
            if etiquetas:
                tags = [tag.strip() for tag in etiquetas.split(',') if tag.strip()]
                contenido_completo += "---\n"
                contenido_completo += f"tags: {tags}\n"
                contenido_completo += f"created: {datetime.now().isoformat()}\n"
                contenido_completo += "---\n\n"
            
            # Agregar título como header
            contenido_completo += f"# {titulo}\n\n"
            contenido_completo += contenido
            
            # Escribir archivo
            with open(nota_path, 'w', encoding='utf-8') as f:
                f.write(contenido_completo)
            
            ruta_relativa = nota_path.relative_to(vault_path)
            return (
                f"✅ Nota creada: {ruta_relativa}\n"
                f"📄 Título: {titulo}\n"
                f"📁 Ubicación: {carpeta or 'raíz'}\n"
                f"🏷️ Etiquetas: {etiquetas or 'ninguna'}"
            )
            
        except Exception as e:
            return f"❌ Error al crear nota: {e}"

    @mcp.tool()
    def agregar_a_nota(nombre_archivo: str, contenido: str, al_final: bool = True) -> str:
        """
        Agrega contenido a una nota existente
        
        Args:
            nombre_archivo: Nombre del archivo a modificar
            contenido: Contenido a agregar
            al_final: Si agregar al final (True) o al principio (False) de la nota
        """
        try:
            vault_path = get_vault_path()
            nota_path = find_note_by_name(nombre_archivo)
            
            if not nota_path:
                return f"❌ No se encontró la nota '{nombre_archivo}'"
            
            # Leer contenido actual
            with open(nota_path, 'r', encoding='utf-8') as f:
                contenido_actual = f.read()
            
            # Preparar nuevo contenido
            if al_final:
                nuevo_contenido = contenido_actual + "\n\n" + contenido
            else:
                # Si hay frontmatter, agregar después de él
                if contenido_actual.startswith('---'):
                    partes = contenido_actual.split('---', 2)
                    if len(partes) >= 3:
                        nuevo_contenido = f"---{partes[1]}---\n\n{contenido}\n\n{partes[2]}"
                    else:
                        nuevo_contenido = contenido + "\n\n" + contenido_actual
                else:
                    nuevo_contenido = contenido + "\n\n" + contenido_actual
            
            # Escribir archivo actualizado
            with open(nota_path, 'w', encoding='utf-8') as f:
                f.write(nuevo_contenido)
            
            ruta_relativa = nota_path.relative_to(vault_path)
            posicion = "al final" if al_final else "al principio"
            return f"✅ Contenido agregado {posicion} de la nota: {ruta_relativa}"
            
        except Exception as e:
            return f"❌ Error al agregar contenido: {e}"

    @mcp.tool()
    def eliminar_nota(nombre_archivo: str, confirmar: bool = False) -> str:
        """
        Elimina una nota del vault (requiere confirmación)
        
        Args:
            nombre_archivo: Nombre del archivo a eliminar
            confirmar: Confirmación para eliminar (debe ser True)
        """
        try:
            if not confirmar:
                return "❌ Para eliminar una nota, debes establecer confirmar=True"
            
            vault_path = get_vault_path()
            nota_path = find_note_by_name(nombre_archivo)
            
            if not nota_path:
                return f"❌ No se encontró la nota '{nombre_archivo}'"
            
            ruta_relativa = nota_path.relative_to(vault_path)
            
            # Eliminar archivo
            nota_path.unlink()
            
            return f"✅ Nota eliminada: {ruta_relativa}"
            
        except Exception as e:
            return f"❌ Error al eliminar nota: {e}"

    @mcp.tool()
    def renombrar_nota(nombre_actual: str, nombre_nuevo: str) -> str:
        """
        Renombra una nota en el vault
        
        Args:
            nombre_actual: Nombre actual del archivo
            nombre_nuevo: Nuevo nombre para el archivo
        """
        try:
            vault_path = get_vault_path()
            nota_path = find_note_by_name(nombre_actual)
            
            if not nota_path:
                return f"❌ No se encontró la nota '{nombre_actual}'"
            
            # Preparar nuevo nombre
            nuevo_nombre_sanitizado = sanitize_filename(nombre_nuevo)
            nueva_ruta = nota_path.parent / nuevo_nombre_sanitizado
            
            # Verificar que no exista ya
            if nueva_ruta.exists():
                return f"❌ Ya existe una nota con el nombre '{nuevo_nombre_sanitizado}'"
            
            # Renombrar archivo
            nota_path.rename(nueva_ruta)
            
            ruta_relativa_anterior = nota_path.relative_to(vault_path)
            ruta_relativa_nueva = nueva_ruta.relative_to(vault_path)
            
            return (
                f"✅ Nota renombrada:\n"
                f"📄 De: {ruta_relativa_anterior}\n"
                f"📄 A: {ruta_relativa_nueva}"
            )
            
        except Exception as e:
            return f"❌ Error al renombrar nota: {e}"
