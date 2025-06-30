"""
Servidor MCP para Obsidian - Gestión avanzada de tu vault
Permite interactuar con tu vault de Obsidian desde Claude
"""

import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

# Cargar variables de entorno
load_dotenv()

# Configuración del vault de Obsidian desde variable de entorno
OBSIDIAN_VAULT_PATH = os.getenv('OBSIDIAN_VAULT_PATH')

if not OBSIDIAN_VAULT_PATH:
    raise ValueError("❌ La variable de entorno OBSIDIAN_VAULT_PATH no está configurada")

# Crear el servidor MCP
mcp = FastMCP("Obsidian MCP Server")

# ========== HERRAMIENTAS DE NAVEGACIÓN ==========

@mcp.tool()
def listar_notas(carpeta: str = "", incluir_subcarpetas: bool = True) -> str:
    """
    Lista todas las notas (.md) en el vault o en una carpeta específica
    
    Args:
        carpeta: Carpeta específica a explorar (vacío = raíz del vault)
        incluir_subcarpetas: Si incluir subcarpetas en la búsqueda
    """
    try:
        vault_path = Path(OBSIDIAN_VAULT_PATH)
        if carpeta:
            target_path = vault_path / carpeta
            if not target_path.exists():
                return f"❌ La carpeta '{carpeta}' no existe en el vault"
        else:
            target_path = vault_path
        
        # Buscar archivos markdown
        if incluir_subcarpetas:
            pattern = "**/*.md"
        else:
            pattern = "*.md"
        
        notas = list(target_path.glob(pattern))
        
        if not notas:
            return f"📂 No se encontraron notas en '{carpeta or 'raíz'}'"
        
        # Organizar por carpetas
        notas_por_carpeta = {}
        for nota in notas:
            # Obtener ruta relativa al vault
            ruta_relativa = nota.relative_to(vault_path)
            carpeta_padre = str(ruta_relativa.parent) if ruta_relativa.parent != Path('.') else "📄 Raíz"
            
            if carpeta_padre not in notas_por_carpeta:
                notas_por_carpeta[carpeta_padre] = []
            
            # Información de la nota
            stats = nota.stat()
            size_kb = stats.st_size / 1024
            modified = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M')
            
            notas_por_carpeta[carpeta_padre].append({
                'nombre': nota.name,
                'ruta': str(ruta_relativa),
                'tamaño': f"{size_kb:.1f}KB",
                'modificado': modified
            })
        
        # Formatear resultado
        resultado = f"📚 Notas encontradas en el vault ({len(notas)} total):\n\n"
        
        for carpeta_nombre, lista_notas in sorted(notas_por_carpeta.items()):
            resultado += f"📁 {carpeta_nombre} ({len(lista_notas)} notas):\n"
            for nota in sorted(lista_notas, key=lambda x: x['nombre']):
                resultado += f"   📄 {nota['nombre']} ({nota['tamaño']}, {nota['modificado']})\n"
            resultado += "\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al listar notas: {e}"

@mcp.tool()
def leer_nota(nombre_archivo: str) -> str:
    """
    Lee el contenido completo de una nota específica
    
    Args:
        nombre_archivo: Nombre del archivo (puede incluir ruta, ej: "Diario/2024-01-01.md")
    """
    try:
        vault_path = Path(OBSIDIAN_VAULT_PATH)
        
        # Buscar el archivo (puede estar en cualquier subcarpeta)
        nota_path = None
        
        # Si incluye ruta, buscar directamente
        if "/" in nombre_archivo:
            nota_path = vault_path / nombre_archivo
        else:
            # Buscar en todo el vault
            for archivo in vault_path.rglob("*.md"):
                if archivo.name == nombre_archivo or archivo.stem == nombre_archivo:
                    nota_path = archivo
                    break
        
        if not nota_path or not nota_path.exists():
            return f"❌ No se encontró la nota '{nombre_archivo}'"
        
        # Leer contenido
        with open(nota_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Información del archivo
        stats = nota_path.stat()
        size_kb = stats.st_size / 1024
        modified = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M')
        ruta_relativa = nota_path.relative_to(vault_path)
        
        resultado = f"📄 **{nota_path.name}**\n"
        resultado += f"📍 Ubicación: {ruta_relativa}\n"
        resultado += f"📊 Tamaño: {size_kb:.1f}KB | Modificado: {modified}\n"
        resultado += f"{'=' * 50}\n\n"
        resultado += contenido
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al leer nota: {e}"

@mcp.tool()
def buscar_en_notas(texto: str, carpeta: str = "", solo_titulos: bool = False) -> str:
    """
    Busca texto en las notas del vault
    
    Args:
        texto: Texto a buscar
        carpeta: Carpeta específica donde buscar (vacío = todo el vault)
        solo_titulos: Si buscar solo en los títulos de las notas
    """
    try:
        vault_path = Path(OBSIDIAN_VAULT_PATH)
        if carpeta:
            search_path = vault_path / carpeta
            if not search_path.exists():
                return f"❌ La carpeta '{carpeta}' no existe"
        else:
            search_path = vault_path
        
        resultados = []
        archivos_revisados = 0
        
        for archivo in search_path.rglob("*.md"):
            archivos_revisados += 1
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                
                ruta_relativa = archivo.relative_to(vault_path)
                
                if solo_titulos:
                    # Buscar solo en el nombre del archivo
                    if texto.lower() in archivo.stem.lower():
                        resultados.append({
                            'archivo': str(ruta_relativa),
                            'tipo': 'título',
                            'coincidencia': archivo.stem
                        })
                else:
                    # Buscar en todo el contenido
                    lineas = contenido.split('\n')
                    for num_linea, linea in enumerate(lineas, 1):
                        if texto.lower() in linea.lower():
                            resultados.append({
                                'archivo': str(ruta_relativa),
                                'linea': num_linea,
                                'coincidencia': linea.strip()[:100] + "..." if len(linea.strip()) > 100 else linea.strip()
                            })
            except:
                continue
        
        if not resultados:
            busqueda_tipo = "títulos" if solo_titulos else "contenido"
            return f"🔍 No se encontró '{texto}' en {busqueda_tipo} de {archivos_revisados} notas"
        
        # Formatear resultados
        busqueda_tipo = "títulos" if solo_titulos else "contenido"
        resultado = f"🔍 Búsqueda de '{texto}' en {busqueda_tipo} ({len(resultados)} coincidencias):\n\n"
        
        # Agrupar por archivo
        por_archivo = {}
        for r in resultados:
            archivo = r['archivo']
            if archivo not in por_archivo:
                por_archivo[archivo] = []
            por_archivo[archivo].append(r)
        
        for archivo, coincidencias in list(por_archivo.items())[:20]:  # Limitar a 20 archivos
            resultado += f"📄 **{archivo}** ({len(coincidencias)} coincidencias):\n"
            for coincidencia in coincidencias[:5]:  # Máximo 5 coincidencias por archivo
                if solo_titulos:
                    resultado += f"   📌 {coincidencia['coincidencia']}\n"
                else:
                    resultado += f"   📍 Línea {coincidencia['linea']}: {coincidencia['coincidencia']}\n"
            if len(coincidencias) > 5:
                resultado += f"   ... y {len(coincidencias) - 5} coincidencias más\n"
            resultado += "\n"
        
        if len(por_archivo) > 20:
            resultado += f"... y {len(por_archivo) - 20} archivos más con coincidencias"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error en búsqueda: {e}"

# ========== HERRAMIENTAS DE CREACIÓN ==========

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
        vault_path = Path(OBSIDIAN_VAULT_PATH)
        
        # Preparar nombre de archivo
        nombre_archivo = titulo.replace('/', '-').replace('\\', '-')
        if not nombre_archivo.endswith('.md'):
            nombre_archivo += '.md'
        
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
        return f"✅ Nota creada: {ruta_relativa}\n📄 Título: {titulo}\n📁 Ubicación: {carpeta or 'raíz'}\n🏷️ Etiquetas: {etiquetas or 'ninguna'}"
        
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
        vault_path = Path(OBSIDIAN_VAULT_PATH)
        
        # Buscar el archivo
        nota_path = None
        if "/" in nombre_archivo:
            nota_path = vault_path / nombre_archivo
        else:
            for archivo in vault_path.rglob("*.md"):
                if archivo.name == nombre_archivo or archivo.stem == nombre_archivo:
                    nota_path = archivo
                    break
        
        if not nota_path or not nota_path.exists():
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

# ========== HERRAMIENTAS DE ANÁLISIS ==========

@mcp.tool()
def estadisticas_vault() -> str:
    """
    Genera estadísticas completas del vault de Obsidian
    """
    try:
        vault_path = Path(OBSIDIAN_VAULT_PATH)
        vault_name = vault_path.name
        
        # Contadores
        total_notas = 0
        total_palabras = 0
        total_caracteres = 0
        carpetas = set()
        etiquetas = set()
        enlaces_internos = set()
        
        # Análisis por fecha
        por_fecha = {}
        
        for archivo in vault_path.rglob("*.md"):
            total_notas += 1
            
            # Carpeta
            carpeta_padre = archivo.parent.relative_to(vault_path)
            if str(carpeta_padre) != '.':
                carpetas.add(str(carpeta_padre))
            
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                
                # Contar palabras y caracteres
                palabras = len(contenido.split())
                total_palabras += palabras
                total_caracteres += len(contenido)
                
                # Buscar etiquetas (#tag)
                tags_encontrados = re.findall(r'#(\w+)', contenido)
                etiquetas.update(tags_encontrados)
                
                # Buscar enlaces internos [[link]]
                enlaces_encontrados = re.findall(r'\[\[([^\]]+)\]\]', contenido)
                enlaces_internos.update(enlaces_encontrados)
                
                # Fecha de modificación
                fecha_mod = datetime.fromtimestamp(archivo.stat().st_mtime).date()
                fecha_str = fecha_mod.strftime('%Y-%m')
                por_fecha[fecha_str] = por_fecha.get(fecha_str, 0) + 1
                
            except:
                continue
        
        # Formatear estadísticas
        resultado = f"📊 **Estadísticas del Vault '{vault_name}'**\n\n"
        
        resultado += f"📚 **Contenido:**\n"
        resultado += f"   • Total de notas: {total_notas:,}\n"
        resultado += f"   • Total de palabras: {total_palabras:,}\n"
        resultado += f"   • Total de caracteres: {total_caracteres:,}\n"
        resultado += f"   • Promedio de palabras por nota: {total_palabras/max(total_notas,1):.0f}\n\n"
        
        resultado += f"📁 **Organización:**\n"
        resultado += f"   • Carpetas: {len(carpetas)}\n"
        for carpeta in sorted(carpetas):
            resultado += f"     - {carpeta}\n"
        resultado += "\n"
        
        resultado += f"🏷️ **Etiquetas más usadas:**\n"
        if etiquetas:
            # Contar frecuencia de etiquetas (simplificado)
            for tag in sorted(list(etiquetas)[:10]):
                resultado += f"   • #{tag}\n"
        else:
            resultado += "   • No se encontraron etiquetas\n"
        resultado += "\n"
        
        resultado += f"🔗 **Enlaces internos únicos:** {len(enlaces_internos)}\n\n"
        
        resultado += f"📅 **Actividad por mes (últimos 6 meses):**\n"
        for fecha in sorted(list(por_fecha.keys()))[-6:]:
            resultado += f"   • {fecha}: {por_fecha[fecha]} notas\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al generar estadísticas: {e}"

@mcp.tool()
def buscar_notas_por_fecha(fecha_desde: str, fecha_hasta: str = "") -> str:
    """
    Busca notas modificadas en un rango de fechas
    
    Args:
        fecha_desde: Fecha de inicio (YYYY-MM-DD)
        fecha_hasta: Fecha de fin (YYYY-MM-DD, opcional, por defecto hoy)
    """
    try:
        vault_path = Path(OBSIDIAN_VAULT_PATH)
        
        # Parsear fechas
        fecha_inicio = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
        if fecha_hasta:
            fecha_fin = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
        else:
            fecha_fin = date.today()
        
        notas_encontradas = []
        
        for archivo in vault_path.rglob("*.md"):
            fecha_mod = datetime.fromtimestamp(archivo.stat().st_mtime).date()
            
            if fecha_inicio <= fecha_mod <= fecha_fin:
                ruta_relativa = archivo.relative_to(vault_path)
                stats = archivo.stat()
                
                notas_encontradas.append({
                    'nombre': archivo.name,
                    'ruta': str(ruta_relativa),
                    'fecha': fecha_mod.strftime('%Y-%m-%d'),
                    'tamaño': f"{stats.st_size/1024:.1f}KB"
                })
        
        if not notas_encontradas:
            return f"📅 No se encontraron notas modificadas entre {fecha_desde} y {fecha_fin}"
        
        # Ordenar por fecha (más recientes primero)
        notas_encontradas.sort(key=lambda x: x['fecha'], reverse=True)
        
        resultado = f"📅 Notas modificadas entre {fecha_desde} y {fecha_fin} ({len(notas_encontradas)} encontradas):\n\n"
        
        for nota in notas_encontradas:
            resultado += f"📄 {nota['nombre']} ({nota['tamaño']})\n"
            resultado += f"   📍 {nota['ruta']} | 📅 {nota['fecha']}\n\n"
        
        return resultado
        
    except ValueError:
        return "❌ Formato de fecha inválido. Usa YYYY-MM-DD (ej: 2024-01-15)"
    except Exception as e:
        return f"❌ Error al buscar por fecha: {e}"

# ========== RECURSOS ==========

@mcp.resource("obsidian://vault_info")
async def info_vault() -> str:
    """Información general del vault de Obsidian"""
    vault_path = Path(OBSIDIAN_VAULT_PATH)
    
    info = {
        "vault_path": str(vault_path),
        "vault_name": vault_path.name,
        "exists": vault_path.exists(),
        "total_files": len(list(vault_path.rglob("*.*"))) if vault_path.exists() else 0,
        "markdown_files": len(list(vault_path.rglob("*.md"))) if vault_path.exists() else 0,
        "last_scan": datetime.now().isoformat()
    }
    
    return json.dumps(info, indent=2, ensure_ascii=False)

# ========== PROMPTS ==========

@mcp.prompt()
def prompt_asistente_obsidian() -> str:
    """Prompt especializado para gestión de Obsidian"""
    vault_name = Path(OBSIDIAN_VAULT_PATH).name
    return f"""
    Soy tu asistente especializado para el vault de Obsidian '{vault_name}'.
    
    🧠 **CAPACIDADES DISPONIBLES:**
    
    📚 **NAVEGACIÓN Y BÚSQUEDA:**
    - listar_notas(): Ve todas las notas del vault organizadas por carpetas
    - leer_nota(nombre): Lee el contenido completo de cualquier nota
    - buscar_en_notas(texto): Busca contenido específico en todas las notas
    - buscar_notas_por_fecha(): Encuentra notas por rango de fechas
    
    ✍️ **CREACIÓN Y EDICIÓN:**
    - crear_nota(titulo, contenido, carpeta, etiquetas): Crea nuevas notas
    - agregar_a_nota(archivo, contenido): Agrega contenido a notas existentes
    
    📊 **ANÁLISIS:**
    - estadisticas_vault(): Estadísticas completas del vault
    
    💡 **SUGERENCIAS DE USO:**
    • "Muéstrame mis notas más recientes"
    • "Busca todas las referencias a 'inteligencia artificial'"
    • "Crea una nota sobre lo que he aprendido hoy"
    • "¿Cuáles son mis temas más frecuentes?"
    • "Lee mi nota sobre meditaciones"
    
    ¿En qué puedo ayudarte con tu vault de Obsidian?
    """

if __name__ == "__main__":
    # Verificar que el vault existe
    if not Path(OBSIDIAN_VAULT_PATH).exists():
        print(f"❌ Error: No se encontró el vault en {OBSIDIAN_VAULT_PATH}")
        exit(1)
    
    print(f"🧠 Iniciando servidor MCP para Obsidian vault: {OBSIDIAN_VAULT_PATH}")
    mcp.run()
