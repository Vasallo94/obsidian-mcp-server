# Tool Reference

This guide details all the tools available in the Obsidian MCP server, organized by their functional domain.

## Navigation and Inspection
Tools to explore and read the vault's content.

- **`listar_notas(carpeta, incluir_subcarpetas)`**: Returns a list of `.md` files. Allows filtering by subfolder.
- **`leer_nota(nombre_archivo)`**: Returns the complete content of a note, including its YAML frontmatter.
- **`buscar_en_notas(texto, carpeta, solo_titulos)`**: Performs a full-text search or title-only search.
- **`buscar_notas_por_fecha(fecha_desde, fecha_hasta)`**: Finds notes modified within a time range.
- **`leer_contexto_vault()`**: Provides a summary of the structure, common tags, and available templates.

## Creation and Editing
Tools to manipulate information.

- **`crear_nota(titulo, contenido, carpeta, etiquetas, plantilla, agente_creador)`**: Creates a new note. Supports templates from the templates folder (auto-detected or configured in `vault.yaml`).
- **`editar_nota(nombre_archivo, nuevo_contenido)`**: Replaces a note's content. It is recommended to read it first.
- **`agregar_a_nota(nombre_archivo, contenido, al_final)`**: Appends or prepends text to an existing note.
- **`sugerir_ubicacion(titulo, contenido, etiquetas)`**: Suggests folders using **RAG semantic search**. Finds similar notes whose folders "vote" for the best location. Returns multiple candidates with confidence scores. See [Semantic Search](semantic-search.md#4-sugerir_ubicacion-folder-recommendation) for details.
- **`mover_nota(origen, destino, crear_carpetas)`**: Renames or moves files, managing directory creation if necessary.
- **`eliminar_nota(nombre_archivo, confirmar)`**: Deletes a note upon confirmation.

## Analysis and Quality
Tools to maintain vault consistency.

- **`estadisticas_vault()`**: Detailed report on the number of notes, tags, links, and vault size.
- **`obtener_tags_canonicas()`**: Reads allowed tags from the official registry file.
- **`analizar_etiquetas()`**: Compares tags used in notes against the official ones.
- **`sincronizar_registro_tags(actualizar)`**: Updates statistics in the tag registry file.
- **`obtener_lista_etiquetas()`**: Simple list of all unique tags present in the vault.
- **`resumen_actividad_reciente(dias)`**: Summary of changes made to the vault in the last week.

## Graphs and Connections
Tools to navigate the knowledge network.

- **`obtener_backlinks(nombre_nota)`**: Lists all notes mentioning the current note.
- **`obtener_notas_por_tag(tag)`**: Filters notes by a specific tag.
- **`obtener_grafo_local(nombre_nota, profundidad)`**: Explores direct and indirect connections of a note.
- **`encontrar_notas_huerfanas()`**: Identifies notes with no incoming or outgoing links.

## Semantic Search (RAG)
Tools based on AI and embeddings.

- **`preguntar_al_conocimiento(pregunta, metadata_filter)`**: Natural language search over the vault's content.
- **`indexar_vault_semantico(forzar)`**: Updates the vector index (ChromaDB) with the latest changes.
- **`encontrar_conexiones_sugeridas(threshold, limite)`**: Finds similar notes that are not yet linked.

## YouTube
- **`get_youtube_transcript(url, language)`**: Downloads a video's transcript to process it like any other note.

## Skills (Agents)

Skills are specialized personalities or roles defined in **your Obsidian vault** (not in the MCP repository). They are stored in the `.agents/skills/` folder within your vault.

> **Important**: These tools read files from your vault, not from the MCP server configuration.

- **`listar_agentes()`**: Lists available skills in `{your_vault}/.agents/skills/`.
- **`obtener_instrucciones_agente(nombre)`**: Reads the content of a specific skill (`SKILL.md`).
- **`obtener_reglas_globales()`**: Reads global rules from `{your_vault}/.agents/GLOBAL_RULES.md`.
- **`refrescar_cache_skills()`**: Invalidates the skills cache (useful after editing files).
