"""
Core business logic for analysis tools.

This module contains the actual implementation of vault analysis operations,
separated from the MCP tool registration to improve testability and
maintain single responsibility.

All functions return Result[str] for consistent error handling.
"""

import re
from datetime import datetime, timedelta

from ..config import get_vault_path
from ..result import Result
from ..utils import extract_internal_links, extract_tags_from_content, get_logger

logger = get_logger(__name__)

# Pattern to detect hex color codes used as tags (e.g., #fff, #0f0f0f)
HEX_COLOR_PATTERN = re.compile(r"^([0-9a-fA-F]{3}){1,2}$")


def get_vault_stats() -> Result[str]:
    """Generate complete vault statistics.

    Returns:
        Result with formatted statistics string.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    vault_name = vault_path.name

    # Counters
    total_notas = 0
    total_palabras = 0
    total_caracteres = 0
    carpetas: set[str] = set()
    etiquetas: set[str] = set()
    enlaces_internos: set[str] = set()

    # Analysis by date
    por_fecha: dict[str, int] = {}

    for archivo in vault_path.rglob("*.md"):
        total_notas += 1

        # Folder
        carpeta_padre = archivo.parent.relative_to(vault_path)
        if str(carpeta_padre) != ".":
            carpetas.add(str(carpeta_padre))

        try:
            with open(archivo, "r", encoding="utf-8") as f:
                contenido = f.read()

            # Count words and characters
            palabras = len(contenido.split())
            total_palabras += palabras
            total_caracteres += len(contenido)

            # Find tags and links
            etiquetas.update(extract_tags_from_content(contenido))
            enlaces_internos.update(extract_internal_links(contenido))

            # Modification date
            fecha_mod = datetime.fromtimestamp(archivo.stat().st_mtime).date()
            fecha_str = fecha_mod.strftime("%Y-%m")
            por_fecha[fecha_str] = por_fecha.get(fecha_str, 0) + 1

        except OSError as e:
            logger.debug("No se pudo leer '%s': %s", archivo, e)
            continue

    # Format statistics
    resultado = f"📊 **Estadísticas del Vault '{vault_name}'**\n\n"

    resultado += "📚 **Contenido:**\n"
    resultado += f"   • Total de notas: {total_notas:,}\n"
    resultado += f"   • Total de palabras: {total_palabras:,}\n"
    resultado += f"   • Total de caracteres: {total_caracteres:,}\n"
    promedio_palabras = total_palabras / max(total_notas, 1)
    resultado += f"   • Promedio de palabras por nota: {promedio_palabras:.0f}\n\n"

    resultado += "📁 **Organización:**\n"
    resultado += f"   • Carpetas: {len(carpetas)}\n"
    for carpeta in sorted(carpetas):
        resultado += f"     - {carpeta}\n"
    resultado += "\n"

    resultado += "🏷️ **Etiquetas más usadas:**\n"
    if etiquetas:
        for tag in sorted(list(etiquetas)[:10]):
            resultado += f"   • #{tag}\n"
        if len(etiquetas) > 10:
            resultado += f"   ... y {len(etiquetas) - 10} etiquetas más\n"
    else:
        resultado += "   • No se encontraron etiquetas\n"
    resultado += "\n"

    resultado += f"🔗 **Enlaces internos únicos:** {len(enlaces_internos)}\n\n"

    resultado += "📅 **Actividad por mes (últimos 6 meses):**\n"
    fechas_ordenadas = sorted(list(por_fecha.keys()))[-6:]
    for fecha in fechas_ordenadas:
        resultado += f"   • {fecha}: {por_fecha[fecha]} notas\n"

    return Result.ok(resultado)


def get_canonical_tags() -> Result[str]:
    """Get official/canonical tags from the registry file.

    Returns:
        Result with formatted list of canonical tags.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    registry_path = (
        vault_path / "04_Recursos" / "Obsidian" / "Registro de Tags del Vault.md"
    )

    if not registry_path.exists():
        return Result.fail(
            "No se encontró el archivo de registro en "
            "'04_Recursos/Obsidian/Registro de Tags del Vault.md'."
        )

    with open(registry_path, "r", encoding="utf-8") as f:
        contenido = f.read()

    # Extract tags
    tags_encontradas = re.findall(r"- `([^`]+)`", contenido)

    if not tags_encontradas:
        return Result.fail(
            "No se pudieron extraer tags del registro (formato inesperado)."
        )

    return Result.ok(
        "📋 **Tags Canónicas (del Registro):**\n"
        + ", ".join(sorted(set(tags_encontradas)))
    )


def analyze_tags() -> Result[str]:
    """Analyze tag usage in the vault and compare with official registry.

    Returns:
        Result with formatted tag analysis.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    # Read canonical tags
    registry_path = (
        vault_path / "04_Recursos" / "Obsidian" / "Registro de Tags del Vault.md"
    )
    tags_canonicas: set[str] = set()
    if registry_path.exists():
        with open(registry_path, "r", encoding="utf-8") as f:
            tags_canonicas = set(re.findall(r"- `([^`]+)`", f.read()))

    # Tag counter with frequency
    conteo_etiquetas: dict[str, int] = {}
    archivos_con_etiquetas: list[str] = []

    for archivo in vault_path.rglob("*.md"):
        try:
            # Ignore system folders or registry
            is_sys = ".github" in str(archivo)
            is_reg = "Registro de Tags" in archivo.name
            if is_sys or is_reg:
                continue

            with open(archivo, "r", encoding="utf-8") as f:
                contenido = f.read()

            etiquetas = extract_tags_from_content(contenido)
            if etiquetas:
                archivos_con_etiquetas.append(archivo.name)
                for tag in etiquetas:
                    conteo_etiquetas[tag] = conteo_etiquetas.get(tag, 0) + 1

        except OSError as e:
            logger.debug("No se pudo leer '%s': %s", archivo, e)
            continue

    if not conteo_etiquetas:
        return Result.ok("🏷️ No se encontraron etiquetas en el vault")

    # Separate garbage hex color tags from legitimate tags
    tags_hex_basura = {
        tag: count
        for tag, count in conteo_etiquetas.items()
        if HEX_COLOR_PATTERN.match(tag)
    }
    tags_validas = {
        tag: count
        for tag, count in conteo_etiquetas.items()
        if not HEX_COLOR_PATTERN.match(tag)
    }

    # Identify unofficial tags (only from valid tags)
    tags_no_oficiales = {tag for tag in tags_validas if tag not in tags_canonicas}

    # Sort by frequency (only valid tags)
    etiquetas_ordenadas = sorted(tags_validas.items(), key=lambda x: x[1], reverse=True)

    resultado = "🏷️ **Análisis de Etiquetas**\n\n"
    resultado += "📊 **Resumen:**\n"
    resultado += f"   • Total de etiquetas únicas: {len(tags_validas)}\n"
    resultado += f"   • Archivos con etiquetas: {len(archivos_con_etiquetas)}\n"
    resultado += f"   • **Tags NO oficiales**: {len(tags_no_oficiales)}\n"
    if tags_hex_basura:
        resultado += f"   • ⚠️ **Tags basura (hex)**: {len(tags_hex_basura)}\n"
    resultado += "\n"

    resultado += "🔝 **Etiquetas más frecuentes:**\n"
    for tag, count in etiquetas_ordenadas[:10]:
        marcador = "✅" if tag in tags_canonicas else "⚠️"
        resultado += f"   • {marcador} #{tag}: {count} usos\n"

    if tags_no_oficiales:
        resultado += "\n🚩 **Tags que no están en el registro:**\n"
        tags_no_of_list = sorted(list(tags_no_oficiales))[:10]
        for tag in tags_no_of_list:
            resultado += f"   • #{tag}\n"
        if len(tags_no_oficiales) > 10:
            diff = len(tags_no_oficiales) - 10
            resultado += f"   ... y {diff} más\n"

    # Report garbage hex tags
    if tags_hex_basura:
        resultado += "\n🗑️ **Tags Basura (códigos de color CSS):**\n"
        for tag, count in sorted(
            tags_hex_basura.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            resultado += f"   • `#{tag}` ({count} usos)\n"
        if len(tags_hex_basura) > 5:
            resultado += f"   ... y {len(tags_hex_basura) - 5} más\n"
        resultado += "💡 *Tip: Usa `buscar_y_reemplazar_global` para limpiarlos.*\n"

    return Result.ok(resultado)


def sync_tag_registry(actualizar: bool = False) -> Result[str]:
    """Synchronize tag usage with official registry.

    Args:
        actualizar: If True, update the stats table in the registry file.

    Returns:
        Result with sync report.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    registry_path = (
        vault_path / "04_Recursos" / "Obsidian" / "Registro de Tags del Vault.md"
    )
    if not registry_path.exists():
        return Result.fail("No se encontró el registro oficial de tags.")

    # 1. Get tags from reality
    conteo_real: dict[str, int] = {}
    for archivo in vault_path.rglob("*.md"):
        if (
            ".github" in str(archivo)
            or "Registro de Tags" in archivo.name
            or archivo.name.startswith(".")
        ):
            continue
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                tags = extract_tags_from_content(f.read())
                for t in tags:
                    conteo_real[t] = conteo_real.get(t, 0) + 1
        except OSError as e:
            logger.debug("No se pudo leer '%s': %s", archivo, e)
            continue

    # 2. Get tags from registry
    with open(registry_path, "r", encoding="utf-8") as f:
        contenido_registro = f.read()

    tags_registradas = set(re.findall(r"- `([^`]+)`", contenido_registro))

    # 3. Compare
    faltan_en_registro = {t for t in conteo_real if t not in tags_registradas}
    ya_no_se_usan = {t for t in tags_registradas if t not in conteo_real}

    # 4. Generate report
    resultado = "🔄 **Sincronización de Tags**\n\n"
    resultado += f"📊 Reality check: {len(conteo_real)} tags en uso.\n"
    resultado += f"📋 Registro oficial: {len(tags_registradas)} tags registradas.\n\n"

    if faltan_en_registro:
        resultado += "🚩 **Tags en uso que NO están registradas:**\n"
        for t in sorted(list(faltan_en_registro)):
            resultado += f"   • #{t} ({conteo_real[t]} usos)\n"
    else:
        resultado += "✅ Todas las tags en uso están debidamente registradas.\n"

    if ya_no_se_usan:
        resultado += "\n🧹 **Tags registradas que YA NO se usan:**\n"
        for t in sorted(list(ya_no_se_usan)):
            resultado += f"   • #{t}\n"

    # 5. Update logic
    if actualizar and conteo_real:
        nueva_tabla = "| Tag | Frecuencia | Última verificación |\n"
        nueva_tabla += "|-----|-----------|------------------|\n"
        hoy = datetime.now().strftime("%Y-%m-%d")

        sorted_tags = sorted(conteo_real.items(), key=lambda x: (-x[1], x[0]))
        for t, freq in sorted_tags:
            status = "✅" if t in tags_registradas else "⚠️"
            nueva_tabla += f"| {status} {t} | {freq} | {hoy} |\n"

        seccion_header = None
        header_match = re.search(
            r"^(## .*[Ee]stad[ií]sticas.*)$", contenido_registro, re.MULTILINE
        )
        if header_match:
            seccion_header = header_match.group(1)

        if seccion_header and seccion_header in contenido_registro:
            partes = contenido_registro.split(seccion_header, 1)
            # Keep everything after the next section (## ) or end of file
            next_section = re.search(r"\n## ", partes[1])
            resto = partes[1][next_section.start() :] if next_section else ""

            nuevo_contenido = partes[0] + seccion_header + "\n\n" + nueva_tabla + resto

            with open(registry_path, "w", encoding="utf-8") as f:
                f.write(nuevo_contenido)

            resultado += (
                "\n✅ **Registro actualizado**: "
                "La tabla de estadísticas ha sido regenerada."
            )
        else:
            # Section doesn't exist, create it at the end
            nuevo_contenido = (
                contenido_registro.rstrip() + "\n\n## Estadísticas\n\n" + nueva_tabla
            )
            with open(registry_path, "w", encoding="utf-8") as f:
                f.write(nuevo_contenido)

            resultado += (
                "\n✅ **Sección creada y registro actualizado**: "
                "Se añadió la tabla de estadísticas al final del archivo."
            )

    return Result.ok(resultado)


def list_all_tags() -> Result[str]:
    """Get a simple list of all existing tags in the vault.

    Returns:
        Result with formatted tag list.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    etiquetas_set: set[str] = set()

    for archivo in vault_path.rglob("*.md"):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                contenido = f.read()
                tags = extract_tags_from_content(contenido)
                etiquetas_set.update(tags)
        except OSError as e:
            logger.debug("No se pudo leer '%s': %s", archivo, e)
            continue

    if not etiquetas_set:
        return Result.ok("ℹ️ No se encontraron etiquetas.")

    lista_ordenada = sorted(list(etiquetas_set))
    return Result.ok("🏷️ **Etiquetas existentes:**\n" + ", ".join(lista_ordenada))


def analyze_links() -> Result[str]:
    """Analyze internal links in the vault.

    Returns:
        Result with formatted link analysis.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    enlaces_por_archivo: dict[str, list[str]] = {}
    todos_los_enlaces: dict[str, int] = {}
    archivos_existentes = {f.stem for f in vault_path.rglob("*.md")}

    for archivo in vault_path.rglob("*.md"):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                contenido = f.read()

            enlaces = extract_internal_links(contenido)
            if enlaces:
                enlaces_por_archivo[archivo.name] = list(enlaces)
                for enlace in enlaces:
                    todos_los_enlaces[enlace] = todos_los_enlaces.get(enlace, 0) + 1

        except OSError as e:
            logger.debug("No se pudo leer '%s': %s", archivo, e)
            continue

    if not todos_los_enlaces:
        return Result.ok("🔗 No se encontraron enlaces internos en el vault")

    # Analyze broken links
    enlaces_rotos = []
    for enlace in todos_los_enlaces:
        enlace_limpio = enlace.split("|")[0].strip()
        if enlace_limpio not in archivos_existentes:
            enlaces_rotos.append(enlace)

    # Sort by frequency
    enlaces_ordenados = sorted(
        todos_los_enlaces.items(), key=lambda x: x[1], reverse=True
    )

    resultado = "🔗 **Análisis de Enlaces Internos**\n\n"
    resultado += "📊 **Resumen:**\n"
    resultado += f"   • Total de enlaces únicos: {len(todos_los_enlaces)}\n"
    resultado += f"   • Archivos con enlaces: {len(enlaces_por_archivo)}\n"
    resultado += f"   • Total de referencias: {sum(todos_los_enlaces.values())}\n"
    resultado += f"   • Enlaces rotos: {len(enlaces_rotos)}\n\n"

    resultado += "🔝 **Enlaces más referenciados:**\n"
    for enlace, count in enlaces_ordenados[:10]:
        resultado += f"   • [[{enlace}]]: {count} referencias\n"

    if enlaces_rotos:
        resultado += "\n⚠️ **Enlaces rotos encontrados:**\n"
        for enlace in enlaces_rotos[:10]:
            resultado += f"   • [[{enlace}]]\n"
        if len(enlaces_rotos) > 10:
            resultado += f"   ... y {len(enlaces_rotos) - 10} enlaces rotos más\n"

    return Result.ok(resultado)


def get_recent_activity(dias: int = 7) -> Result[str]:
    """Generate a summary of recent vault activity.

    Args:
        dias: Number of days to look back (default 7).

    Returns:
        Result with formatted activity summary.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    fecha_limite = datetime.now() - timedelta(days=dias)

    archivos_recientes: list[dict[str, str]] = []
    archivos_modificados: list[dict[str, str]] = []

    for archivo in vault_path.rglob("*.md"):
        stats = archivo.stat()
        fecha_creacion = datetime.fromtimestamp(stats.st_ctime)
        fecha_modificacion = datetime.fromtimestamp(stats.st_mtime)

        if fecha_creacion >= fecha_limite:
            archivos_recientes.append(
                {
                    "nombre": archivo.name,
                    "fecha": fecha_creacion.strftime("%Y-%m-%d %H:%M"),
                    "tipo": "creado",
                }
            )
        elif fecha_modificacion >= fecha_limite:
            archivos_modificados.append(
                {
                    "nombre": archivo.name,
                    "fecha": fecha_modificacion.strftime("%Y-%m-%d %H:%M"),
                    "tipo": "modificado",
                }
            )

    # Sort by date
    archivos_recientes.sort(key=lambda x: x["fecha"], reverse=True)
    archivos_modificados.sort(key=lambda x: x["fecha"], reverse=True)

    resultado = f"📅 **Actividad Reciente (últimos {dias} días)**\n\n"

    if archivos_recientes:
        resultado += f"✨ **Archivos creados ({len(archivos_recientes)}):**\n"
        for item_rec in archivos_recientes[:10]:
            resultado += f"   • {item_rec['nombre']} - {item_rec['fecha']}\n"
        if len(archivos_recientes) > 10:
            resultado += f"   ... y {len(archivos_recientes) - 10} archivos más\n"
        resultado += "\n"

    if archivos_modificados:
        resultado += f"📝 **Archivos modificados ({len(archivos_modificados)}):**\n"
        for item in archivos_modificados[:10]:
            resultado += f"   • {item['nombre']} - {item['fecha']}\n"
        if len(archivos_modificados) > 10:
            resultado += f"   ... y {len(archivos_modificados) - 10} archivos más\n"

    if not archivos_recientes and not archivos_modificados:
        resultado += f"😴 No hay actividad registrada en los últimos {dias} días"

    return Result.ok(resultado)
