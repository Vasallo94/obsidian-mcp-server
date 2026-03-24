"""
Modelos Pydantic para los inputs de las herramientas MCP.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SugerirUbicacionInput(BaseModel):
    titulo: str = Field(description="Título de la nota.")
    contenido: str = Field(description="Fragmento o contenido total de la nota.")
    etiquetas: str = Field(default="", description="Etiquetas enviadas o planeadas.")


class CrearNotaInput(BaseModel):
    titulo: str = Field(description="Título de la nota.")
    contenido: str = Field(description="Contenido de la nota.")
    carpeta: str = Field(
        default="", description="Carpeta donde crear la nota (vacío = raíz)."
    )
    etiquetas: str = Field(default="", description="Etiquetas separadas por comas.")
    plantilla: str = Field(
        default="", description="Nombre del archivo de plantilla (ej: 'Diario.md')."
    )
    agente_creador: str = Field(
        default="",
        description="Si se creó usando un agente específico (ej: 'escritor').",
    )
    descripcion: str = Field(
        default="",
        description="Descripción breve de la nota (para placeholder {{description}}).",
    )


class AgregarANotaInput(BaseModel):
    nombre_archivo: str = Field(description="Nombre del archivo a modificar.")
    contenido: str = Field(description="Contenido a agregar.")
    al_final: bool = Field(
        default=True,
        description="Si agregar al final (True) o al principio (False) de la nota.",
    )


class EliminarNotaInput(BaseModel):
    nombre_archivo: str = Field(description="Nombre del archivo a eliminar.")
    confirmar: bool = Field(
        default=False, description="Confirmación para eliminar (debe ser True)."
    )


class EditOperation(BaseModel):
    old: str = Field(
        description="Texto exacto a buscar en la nota (debe ser unico). Vacio = reemplazo total."
    )
    new: str = Field(
        description="Texto de reemplazo."
    )


class EditarNotaInput(BaseModel):
    nombre_archivo: str = Field(
        description="Nombre o ruta de la nota a editar (ej: 'Mi Nota.md')."
    )
    operaciones: list[EditOperation] = Field(
        min_length=1,
        description="Lista de operaciones old->new a aplicar (minimo 1)."
    )


class BuscarYReemplazarGlobalInput(BaseModel):
    buscar: str = Field(
        description="Texto o patrón a buscar (texto literal, no regex)."
    )
    reemplazar: str = Field(description="Texto de reemplazo.")
    carpeta: str = Field(
        default="",
        description="Carpeta específica donde buscar (vacío = todo el vault).",
    )
    solo_preview: bool = Field(
        default=True, description="Si True, solo muestra qué cambiaría sin modificar."
    )
    limite: int = Field(
        default=100, description="Máximo de archivos a procesar (seguridad)."
    )


class CapturaRapidaInput(BaseModel):
    texto: str = Field(description="El contenido a capturar.")
    etiquetas: str = Field(
        default="", description="Etiquetas opcionales separadas por comas."
    )


class AgregarEnSeccionInput(BaseModel):
    nombre_archivo: str = Field(description="Nombre de la nota a modificar.")
    seccion: str = Field(
        description="Nombre de la sección (ej: 'Recursos', '## Ideas')."
    )
    contenido: str = Field(description="Contenido a insertar.")
    crear_si_no_existe: bool = Field(
        default=True, description="Si True, crea la sección si no existe."
    )


class ObtenerFrontmatterInput(BaseModel):
    nombre_archivo: str = Field(description="Nombre de la nota a leer.")


class ActualizarFrontmatterInput(BaseModel):
    nombre_archivo: str = Field(description="Nombre de la nota a modificar.")
    frontmatter_updates: str = Field(
        description="JSON string con un diccionario de actualizaciones."
    )
    merge: bool = Field(
        default=True,
        description="Si True, fusiona con el frontmatter existente. Si False, lo reemplaza por completo.",
    )


class GestionarEtiquetasInput(BaseModel):
    nombre_archivo: str = Field(description="Nombre de la nota a modificar.")
    operacion: str = Field(
        description="'add' (añadir), 'remove' (eliminar), o 'list' (listar)."
    )
    etiquetas: str = Field(
        default="", description="Etiquetas separadas por comas (para 'add' o 'remove')."
    )


# --- agents.py inputs ---


class ObtenerInstruccionesAgenteInput(BaseModel):
    nombre: str = Field(
        description="El nombre de la carpeta de la skill (ej: 'escritor')."
    )


class GenerarSkillInput(BaseModel):
    nombre: str = Field(
        description="Identificador de la skill (ej: 'profesor-fisica')."
    )
    descripcion: str = Field(description="Descripción breve de lo que hace la skill.")
    instrucciones: str = Field(description="Instrucciones principales en markdown.")
    herramientas: str = Field(
        default="",
        description="Herramientas separadas por comas (ej: 'read, edit, web').",
    )
    ubicacion_defecto: str = Field(
        default="",
        description="Carpeta por defecto para notas (ej: '02_Aprendizaje/').",
    )


class SincronizarSkillsInput(BaseModel):
    actualizar: bool = Field(
        default=False,
        description="Si True, aplica correcciones. Si False, solo reporta.",
    )


# --- navigation.py inputs ---


class ListarNotasInput(BaseModel):
    carpeta: str = Field(
        default="",
        description="Carpeta específica a explorar (vacío = raíz del vault).",
    )
    incluir_subcarpetas: bool = Field(
        default=True, description="Si incluir subcarpetas en la búsqueda."
    )


class LeerNotaInput(BaseModel):
    nombre_archivo: str = Field(
        description="Nombre del archivo (ej: 'Diario/2024-01-01.md')."
    )


class BuscarEnNotasInput(BaseModel):
    texto: str = Field(description="Texto a buscar (puede incluir múltiples palabras).")
    carpeta: str = Field(
        default="",
        description="Carpeta específica donde buscar (vacío = todo el vault).",
    )
    solo_titulos: bool = Field(
        default=False, description="Si buscar solo en los títulos de las notas."
    )


class BuscarNotasPorFechaInput(BaseModel):
    fecha_desde: str = Field(description="Fecha de inicio (YYYY-MM-DD).")
    fecha_hasta: str = Field(
        default="", description="Fecha de fin (YYYY-MM-DD, opcional, por defecto hoy)."
    )


class MoverNotaInput(BaseModel):
    origen: str = Field(
        description="Ruta relativa actual de la nota (ej: 'Sin titulo.md')."
    )
    destino: str = Field(
        description="Ruta relativa nueva de la nota (ej: '01_Inbox/Nueva Nota.md')."
    )
    crear_carpetas: bool = Field(
        default=True, description="Si crear las carpetas destino si no existen (True)."
    )


class ConceptoAleatorioInput(BaseModel):
    carpeta: str = Field(
        default="",
        description="Carpeta especifica donde buscar (vacio = todo el vault).",
    )


class LeerMultiplesNotasInput(BaseModel):
    rutas: list[str] = Field(
        description="Lista de nombres de archivos o rutas (ej: ['Nota1.md', 'Nota2.md'])."
    )


class ObtenerInfoNotasInput(BaseModel):
    rutas: list[str] = Field(description="Lista de nombres de archivos o rutas.")


# --- analysis.py inputs ---


class SincronizarRegistroTagsInput(BaseModel):
    actualizar: bool = Field(
        default=False,
        description="Si es True, intenta actualizar la tabla de estadísticas.",
    )


class ResumenActividadRecienteInput(BaseModel):
    dias: int = Field(
        default=7, description="Número de días hacia atrás para analizar."
    )


# --- graph.py inputs ---


class ObtenerBacklinksInput(BaseModel):
    nombre_nota: str = Field(description="Nombre de la nota (con o sin .md)")


class ObtenerNotasPorTagInput(BaseModel):
    tag: str = Field(description="Etiqueta a buscar (con o sin #)")


class ObtenerGrafoLocalInput(BaseModel):
    nombre_nota: str = Field(description="Nombre de la nota central")
    profundidad: int = Field(
        default=1, description="Niveles de profundidad (1 = solo conexiones directas)"
    )


# --- youtube.py inputs ---


class GetYoutubeTranscriptInput(BaseModel):
    url: str = Field(description="URL del video de YouTube o ID del video.")
    language: Optional[str] = Field(
        default=None,
        description="Código del idioma opcional (ej: 'es', 'en'). Si se omite, busca subtítulos manuales en el idioma original, o falla al autogenerado del video.",
    )


# --- semantic.py inputs ---


class PreguntarAlConocimientoInput(BaseModel):
    pregunta: str = Field(
        description="La pregunta o tema sobre el que quieres consultar."
    )
    metadata_filter: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Opcional. Filtro de metadatos (ej: {'type': 'poesia'}).",
    )


class IndexarVaultSemanticoInput(BaseModel):
    forzar: bool = Field(
        default=False,
        description="Si es True, borra el índice anterior y lo crea desde cero.",
    )


class EncontrarConexionesSugeridasInput(BaseModel):
    threshold: float = Field(
        default=0.70, description="Nivel de similitud mínima (0.7 a 1.0). Default 0.70."
    )
    limite: int = Field(default=5, description="Máximo de sugerencias.")
    carpetas_incluir: Optional[list[str]] = Field(
        default=None,
        description="Lista de carpetas donde buscar (e.g. ['03_Notas']). Si se omite, busca en todo excepto exclusiones.",
    )
    excluir_mocs: bool = Field(
        default=True, description="Ignorar MOC, Home, Inbox y sistema."
    )
    min_palabras: int = Field(
        default=150, description="Ignorar notas con menos de X palabras."
    )
