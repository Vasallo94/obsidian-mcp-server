# 🧠 Búsqueda Semántica (RAG)

El servidor Obsidian MCP incluye capacidades de **Generación Aumentada por Recuperación (RAG)**, permitiendo que la IA consulte tu vault utilizando lenguaje natural y comprendiendo el contexto más allá de simples palabras clave.

## ¿Cómo funciona?

El sistema utiliza una base de datos vectorial para representar tus notas como "vectores" en un espacio multidimensional. Cuando haces una pregunta, el servidor busca las notas cuyos vectores son más cercanos al vector de tu consulta.

### Componentes Técnicos
- **Embeddings**: Utiliza modelos de lenguaje para convertir texto en representaciones numéricas.
- **Vector Store**: `ChromaDB` se utiliza para almacenar y buscar estos vectores de forma eficiente.
- **Orquestación**: `LangChain` gestiona el flujo de datos entre las notas y el modelo de embeddings.

## Instalación de Dependencias

Esta funcionalidad es opcional y requiere librerías adicionales que pueden aumentar el tamaño de la instalación:

```bash
pip install "obsidian-mcp-server[rag]"
```

## Herramientas Semánticas

### 1. `preguntar_al_conocimiento`
Es la herramienta principal para consultas de tipo "humano".
- **Ejemplo**: "¿Qué he escrito sobre inteligencia artificial en los últimos meses?"
- **Filtros**: Puedes restringir la búsqueda por metadatos (ej: solo notas de tipo "poesía").

### 2. `indexar_vault_semantico`
Las notas nuevas no aparecen automáticamente en la búsqueda semántica. Debes ejecutar esta herramienta periódicamente para actualizar el índice.
- **Incremental**: Solo procesa notas nuevas o modificadas.
- **Forzada**: Reconstruye todo el índice desde cero (útil si cambias de modelo de embeddings).

### 3. `encontrar_conexiones_sugeridas`
Analiza la similitud semántica entre todas tus notas.
- Si dos notas hablan de temas muy parecidos pero no tienen un enlace `[[Nota]]` entre ellas, el servidor las marcará como una conexión sugerida.
- Es ideal para el mantenimiento y el crecimiento orgánico de tu Zettelkasten.

## Almacenamiento de Datos
El índice vectorial se guarda localmente en una carpeta dentro de tu vault (normalmente `.obsidianrag/` o similar), lo que garantiza que tu conocimiento nunca salga de tu control.
