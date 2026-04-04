"""
Herramientas de navegación para el vault de Obsidian
Incluye funciones para listar, leer y buscar notas
"""

from pathlib import Path

from fastmcp import Context, FastMCP

from ..config import get_vault_path
from ..utils import (
    get_logger,
    is_path_forbidden,
)
from .navigation_logic import (
    get_notes_info_logic,
    get_random_concept,
    list_notes,
    move_note,
    read_multiple_notes_logic,
    read_note,
    search_notes_by_date,
)

logger = get_logger(__name__)


def _formatear_resultados(resultados: list, solo_titulos: bool) -> str:
    """Helper para formatear la salida de búsqueda"""
    resultado_str = f"🔍 Encontradas {len(resultados)} coincidencias:\n\n"

    por_archivo: dict[str, list[dict[str, str]]] = {}
    for r in resultados:
        archivo = r["archivo"]
        if archivo not in por_archivo:
            por_archivo[archivo] = []
        por_archivo[archivo].append(r)

    for archivo, coincidencias in list(por_archivo.items())[:20]:
        resultado_str += f"📄 **{archivo}**\n"
        for c in coincidencias:
            if solo_titulos:
                resultado_str += f"   📌 {c['coincidencia']}\n"
            else:
                resultado_str += f"   📍 L{c['linea']}: {c['coincidencia']}\n"
        resultado_str += "\n"

    if len(por_archivo) > 20:
        resultado_str += f"... y {len(por_archivo) - 20} archivos más."

    return resultado_str


def register_navigation_tools(mcp: FastMCP) -> None:  # pylint: disable=too-many-statements
    """
    Registra todas las herramientas de navegación en el servidor MCP

    Args:
        mcp: Instancia del servidor FastMCP
    """

    @mcp.tool()
    def listar_notas(carpeta: str = "", incluir_subcarpetas: bool = True) -> str:
        """
        Lista todas las notas (.md) en el vault o en una carpeta específica

        Args:
            carpeta: Carpeta específica a explorar (vacío = raíz del vault)
            incluir_subcarpetas: Si incluir subcarpetas en la búsqueda
        """
        try:
            return list_notes(carpeta, incluir_subcarpetas).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al listar notas: {e}"

    @mcp.tool()
    def leer_nota(nombre_archivo: str) -> str:
        """
        Lee el contenido completo de una nota especifica

        Args:
            nombre_archivo: Nombre del archivo (ej: "Diario/2024-01-01.md")
        """
        try:
            return read_note(nombre_archivo).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al leer nota: {e}"

    @mcp.tool()
    def buscar_en_notas(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-nested-blocks
        texto: str, carpeta: str = "", solo_titulos: bool = False
    ) -> str:
        """
        Busca texto en las notas del vault usando búsqueda inteligente
        (ripgrep o fallback Python).
        Soporta múltiples términos: "nas ssh" buscará notas que contengan
        "nas" Y "ssh".

        Args:
            texto: Texto a buscar (puede incluir múltiples palabras)
            carpeta: Carpeta específica donde buscar (vacío = todo el vault)
            solo_titulos: Si buscar solo en los títulos de las notas
        """
        import shutil  # pylint: disable=import-outside-toplevel

        # subprocess is required to call the ripgrep binary (rg).
        # Arguments are always passed as a list (never shell=True),
        # preventing injection.
        import subprocess  # pylint: disable=import-outside-toplevel # nosec B404

        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            if carpeta:
                search_path = vault_path / carpeta
                if not search_path.exists():
                    return f"❌ La carpeta '{carpeta}' no existe"
            else:
                search_path = vault_path

            # Preparar términos de búsqueda (AND logic)
            terminos = [t.strip() for t in texto.split() if t.strip()]
            if not terminos:
                return "❌ Debes proporcionar texto para buscar."

            # P3: Tip for short terms (<=3 chars) when not using solo_titulos
            short_term_tip = ""
            short_terms = [t for t in terminos if len(t) <= 3]
            if short_terms and not solo_titulos:
                short_term_tip = (
                    f"💡 **Tip**: Para términos cortos como '{short_terms[0]}', "
                    "considera usar `solo_titulos=True` para mayor precisión.\n\n"
                )

            resultados = []
            archivos_coincidentes = set()
            rg_path = shutil.which("rg")

            # --- ESTRATEGIA: HÍBRIDA (RG + Python) ---
            # 1. Usar ripgrep para encontrar archivos con el PRIMER término
            #    (filtro rápido)
            # 2. Verificar el resto de términos en Python (lógica robusta)
            if rg_path and not solo_titulos:
                try:
                    # Buscar el primer término con rg (solo .md)
                    cmd = [
                        rg_path,
                        "--ignore-case",
                        "--files-with-matches",
                        "--null",
                        "-g",
                        "*.md",
                        terminos[0],
                        str(search_path),
                    ]

                    result = subprocess.run(  # pylint: disable=subprocess-run-check # nosec B603
                        cmd,
                        capture_output=True,
                        check=False,  # No lanzar error si no encuentra nada (retcode 1)
                    )

                    if result.returncode == 0:
                        paths_raw = result.stdout.decode(
                            "utf-8", errors="ignore"
                        ).split("\0")
                        candidatos = [p for p in paths_raw if p]

                        # Si hay más términos, filtrarlos en Python
                        # (más seguro que pipear rg)
                        if len(terminos) > 1:
                            for cand in candidatos:
                                try:
                                    with open(cand, "r", encoding="utf-8") as f:
                                        contenido = f.read().lower()
                                    # Verificar RESTO de términos
                                    if all(
                                        t.lower() in contenido for t in terminos[1:]
                                    ):
                                        archivos_coincidentes.add(cand)
                                except OSError as e:
                                    logger.debug(
                                        "No se pudo leer candidato '%s': %s", cand, e
                                    )
                        else:
                            # Solo había un término, todos son válidos
                            for cand in candidatos:
                                archivos_coincidentes.add(cand)

                except OSError as e:
                    logger.warning("Error en fase RG, cayendo a Python puro: %s", e)
                    rg_path = None  # Forzar fallback

            # --- ESTRATEGIA 2: PYTHON PURO (Fallback o Títulos) ---
            if (not rg_path and not archivos_coincidentes) or solo_titulos:
                # (Mantener lógica original para solo_titulos o fallback total)
                # Si es solo títulos, buscar solo en nombres
                if solo_titulos:
                    for archivo_item in search_path.rglob("*.md"):
                        # Security: Skip forbidden paths
                        is_forbidden_path, _ = is_path_forbidden(
                            archivo_item, vault_path
                        )
                        if is_forbidden_path:
                            continue

                        # Verificar si TODOS los términos están en el nombre
                        nombre_lower = archivo_item.stem.lower()
                        if all(t.lower() in nombre_lower for t in terminos):
                            ruta_relativa = archivo_item.relative_to(vault_path)
                            resultados.append(
                                {
                                    "archivo": str(ruta_relativa),
                                    "tipo": "título",
                                    "coincidencia": archivo_item.stem,
                                }
                            )
                    # Salir rápido si solo buscamos títulos
                    if resultados:
                        return _formatear_resultados(resultados, solo_titulos=True)
                    return f"🔍 No se encontraron notas con el título '{texto}'"

                # Si es contenido (Fallback Python)
                for archivo_item in search_path.rglob("*.md"):
                    # Security
                    is_forbidden_path, _ = is_path_forbidden(archivo_item, vault_path)
                    if is_forbidden_path:
                        continue

                    try:
                        # Leer archivo
                        with open(archivo_item, "r", encoding="utf-8") as f:
                            contenido = f.read().lower()

                        # Verificar AND logic
                        if all(t.lower() in contenido for t in terminos):
                            archivos_coincidentes.add(str(archivo_item))

                    except OSError as e:
                        logger.debug(
                            "No se pudo leer fichero '%s': %s", archivo_item, e
                        )
                        continue

            # --- PROCESAR RESULTADOS DE CONTENIDO ---
            # Si tenemos archivos candidatos (de rg o python), extraemos el contexto
            # Esto es necesario porque rg -l no da el contexto, y queremos mostrarlo

            for archivo_str in archivos_coincidentes:
                archivo_path = Path(archivo_str)
                # Asegurar path absoluto si viene de rg relativo (depende de cwd)
                if not archivo_path.is_absolute():
                    # rg devuelve paths absolutos si input es absoluto,
                    # pero por seguridad:
                    archivo_path = Path(archivo_str).resolve()

                try:
                    # Recalcular relativo para display
                    try:
                        ruta_relativa = archivo_path.relative_to(vault_path)
                    except ValueError:
                        # Si rg devolvió path extraño
                        continue

                    # Security check (redundante pero seguro)
                    is_forbidden_path, _ = is_path_forbidden(archivo_path, vault_path)
                    if is_forbidden_path:
                        continue

                    with open(archivo_path, "r", encoding="utf-8") as f:
                        lineas = f.readlines()

                    # Buscar la MEJOR línea de coincidencia (la que tenga más términos)
                    for num, linea in enumerate(lineas, 1):
                        linea_lower = linea.lower()
                        # Solo mostramos líneas que tengan AL MENOS UNO de los términos
                        # (Ya sabemos que el archivo tiene todos)
                        if any(t.lower() in linea_lower for t in terminos):
                            if len(linea.strip()) > 3:  # Ignorar líneas muy cortas
                                co = (
                                    linea.strip()[:100] + "..."
                                    if len(linea.strip()) > 100
                                    else linea.strip()
                                )
                                resultados.append(
                                    {
                                        "archivo": str(ruta_relativa),
                                        "linea": str(num),
                                        "coincidencia": co,
                                    }
                                )
                                # P3: Límite: solo 2 líneas por archivo (era 3)
                                if (
                                    len(
                                        [
                                            r
                                            for r in resultados
                                            if r["archivo"] == str(ruta_relativa)
                                        ]
                                    )
                                    >= 2
                                ):
                                    break

                except OSError as e:
                    logger.error("Error procesando archivo %s: %s", archivo_str, e)
                    continue

            if not resultados:
                return (
                    f"🔍 No se encontraron notas que contengan: {', '.join(terminos)}"
                )

            return short_term_tip + _formatear_resultados(
                resultados, solo_titulos=False
            )

        except OSError as e:
            logger.error("Error inesperado en busqueda: %s", e)
            return f"❌ Error en búsqueda: {e}"

    @mcp.tool()
    def buscar_notas_por_fecha(fecha_desde: str, fecha_hasta: str = "") -> str:
        """
        Busca notas modificadas en un rango de fechas

        Args:
            fecha_desde: Fecha de inicio (YYYY-MM-DD)
            fecha_hasta: Fecha de fin (YYYY-MM-DD, opcional, por defecto hoy)
        """
        try:
            return search_notes_by_date(fecha_desde, fecha_hasta).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al buscar por fecha: {e}"

    @mcp.tool()
    def mover_nota(origen: str, destino: str, crear_carpetas: bool = True) -> str:
        """
        Mueve o renombra una nota dentro del vault.

        Args:
            origen: Ruta relativa actual de la nota (ej: "Sin titulo.md")
            destino: Ruta relativa nueva de la nota (ej: "01_Inbox/Nueva Nota.md")
            crear_carpetas: Si crear las carpetas destino si no existen (True)

        Returns:
            Mensaje de exito o error.
        """
        try:
            return move_note(origen, destino, crear_carpetas).to_display(
                success_prefix="✅"
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al mover nota: {e}"

    @mcp.tool()
    def concepto_aleatorio(carpeta: str = "") -> str:
        """
        Extrae un concepto aleatorio del vault como flashcard sorpresa.
        Util para reforzar conocimiento o descubrir notas olvidadas.

        Args:
            carpeta: Carpeta especifica donde buscar (vacio = todo el vault)
        """
        try:
            return get_random_concept(carpeta).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error: {e}"

    @mcp.tool()
    async def leer_multiples_notas(rutas: list[str], ctx: Context) -> str:
        """
        Lee el contenido (y frontmatter) de múltiples notas a la vez.
        Útil para ahorrar roundtrips cuando se necesita cargar contexto de varias notas.
        Emite progreso en tiempo real para lotes grandes.

        Args:
            rutas: Lista de nombres de archivos o rutas (ej: ["Nota1.md", "Nota2.md"]).

        Returns:
            JSON string con los resultados de lectura exitosos o errores.
        """
        try:
            total = len(rutas)
            if total > 5:
                await ctx.report_progress(0, total, f"Leyendo {total} notas...")
            result = read_multiple_notes_logic(rutas)
            if total > 5:
                await ctx.report_progress(total, total, "Completado")
            return result.to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al leer múltiples notas: {e}"

    @mcp.tool()
    def obtener_info_notas(rutas: list[str]) -> str:
        """
        Obtiene un desglose rápido de metadatos (tamaño, fecha, frontmatter)
        de múltiples archivos sin cargar todo su contenido.

        Args:
            rutas: Lista de nombres de archivos o rutas.

        Returns:
            JSON string con un array de objetos de metadatos.
        """
        try:
            return get_notes_info_logic(rutas).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al obtener info de notas: {e}"
