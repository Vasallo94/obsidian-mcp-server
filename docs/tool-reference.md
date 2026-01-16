# 🔧 Referencia de Herramientas

Esta guía detalla todas las herramientas disponibles en el servidor Obsidian MCP, organizadas por su dominio funcional.

## 📂 Navegación e Inspección
Herramientas para explorar y leer el contenido del vault.

- **`listar_notas(carpeta, incluir_subcarpetas)`**: Devuelve una lista de archivos `.md`. Permite filtrar por subcarpeta.
- **`leer_nota(nombre_archivo)`**: Devuelve el contenido completo de una nota, incluyendo su frontmatter YAML.
- **`buscar_en_notas(texto, carpeta, solo_titulos)`**: Realiza una búsqueda de texto completo o solo en títulos.
- **`buscar_notas_por_fecha(fecha_desde, fecha_hasta)`**: Encuentra notas modificadas en un rango temporal.
- **`leer_contexto_vault()`**: Proporciona un resumen de la estructura, etiquetas comunes y plantillas disponibles.

## ✍️ Creación y Edición
Herramientas para manipular la información.

- **`crear_nota(titulo, contenido, carpeta, etiquetas, plantilla, agente_creador)`**: Crea una nueva nota. Soporta el uso de plantillas de `ZZ_Plantillas`.
- **`editar_nota(nombre_archivo, nuevo_contenido)`**: Reemplaza el contenido de una nota. Se recomienda leerla primero.
- **`agregar_a_nota(nombre_archivo, contenido, al_final)`**: Añade texto al principio o al final de una nota existente.
- **`sugerir_ubicacion(titulo, contenido, etiquetas)`**: La IA analiza el contenido y sugiere la carpeta más adecuada.
- **`mover_nota(origen, destino, crear_carpetas)`**: Renombra o mueve archivos, gestionando la creación de directorios si es necesario.
- **`eliminar_nota(nombre_archivo, confirmar)`**: Borra una nota previa confirmación.

## 📊 Análisis y Calidad
Herramientas para mantener la consistencia del vault.

- **`estadisticas_vault()`**: Reporte detallado sobre número de notas, etiquetas, enlaces y tamaño del vault.
- **`obtener_tags_canonicas()`**: Lee las etiquetas permitidas desde el archivo de registro oficial.
- **`analizar_etiquetas()`**: Compara las etiquetas usadas en las notas con las oficiales.
- **`sincronizar_registro_tags(actualizar)`**: Actualiza las estadísticas en el archivo de registro de etiquetas.
- **`obtener_lista_etiquetas()`**: Lista simple de todas las etiquetas únicas presentes en el vault.
- **`resumen_actividad_reciente(dias)`**: Resumen de los cambios realizados en el vault en la última semana.

## 🕸️ Grafos y Conexiones
Herramientas para navegar la red de conocimiento.

- **`obtener_backlinks(nombre_nota)`**: Lista todas las notas que mencionan a la nota actual.
- **`obtener_notas_por_tag(tag)`**: Filtra notas por una etiqueta específica.
- **`obtener_grafo_local(nombre_nota, profundidad)`**: Explora las conexiones directas e indirectas de una nota.
- **`encontrar_notas_huerfanas()`**: Identifica notas sin enlaces entrantes ni salientes.

## 🧠 Búsqueda Semántica (RAG)
Herramientas basadas en inteligencia artificial y embeddings.

- **`preguntar_al_conocimiento(pregunta, metadata_filter)`**: Búsqueda en lenguaje natural sobre el contenido del vault.
- **`indexar_vault_semantico(forzar)`**: Actualiza el índice vectorial (ChromaDB) con los últimos cambios.
- **`encontrar_conexiones_sugeridas(threshold, limite)`**: Encuentra notas similares que aún no están enlazadas.

## 📺 YouTube
- **`get_youtube_transcript(url, language)`**: Descarga la transcripción de un video para procesarla como una nota más.

## 🤖 Skills (Agentes)

Las skills son personalidades o roles especializados que defines en **tu vault de Obsidian** (no en el repositorio del MCP). Se almacenan en la carpeta `.agent/skills/` dentro de tu vault.

> **Importante**: Estas herramientas leen archivos desde tu vault, no desde el servidor MCP.

- **`listar_agentes()`**: Lista las skills disponibles en `{tu_vault}/.agent/skills/`.
- **`obtener_instrucciones_agente(nombre)`**: Lee el contenido de una skill específica (`SKILL.md`).
- **`obtener_reglas_globales()`**: Lee las reglas globales desde `{tu_vault}/.agent/REGLAS_GLOBALES.md`.
- **`refrescar_cache_skills()`**: Invalida el caché de skills (útil tras editar archivos).
