---
name: reglas-globales-agentes
description: >
  Protocolo obligatorio que TODOS los agentes deben seguir antes de crear
  o editar notas en el vault.

validations:
  - id: no_emoji_headings
    applies_to: [create, append, edit]
    scope: headings
    pattern: "[\U0001F300-\U0001FFFF\u2600-\u27BF\u2700-\u27BF]"
    warning: "Emojis en cabeceras"

  - id: no_emoji_title
    applies_to: [create]
    scope: title
    pattern: "[\U0001F300-\U0001FFFF\u2600-\u27BF]"
    warning: "Emojis en el titulo de la nota"

  - id: required_frontmatter
    applies_to: [create]
    scope: frontmatter
    required_fields: [type, status, tags]
    warning: "Frontmatter incompleto: faltan {missing_fields}"

  - id: valid_status
    applies_to: [create, edit]
    scope: frontmatter
    field: status
    allowed_values: [captura, en_proceso, completo, archivo]
    warning: "Valor de 'status' invalido: '{value}'"

  - id: valid_type
    applies_to: [create]
    scope: frontmatter
    field: type
    # Sin allowed_values a propósito: el MCP valida contra taxonomy.types
    # de .agents/vault.yaml, la única lista de tipos del vault.
    warning: "Valor de 'type' invalido: '{value}'"

  - id: tags_con_acento
    applies_to: [create, update]
    scope: frontmatter
    field: tags
    rule: "Las tags se escriben en minúscula y con acentos correctos en español (filosofía, psicología, reflexión). Los acrónimos van en minúscula (ia, mcp, rag)."
    warning: "Tag sin acentuar o en mayúsculas: '{value}'"
---

# Reglas Globales para Agentes

> [!CAUTION]
> **OBLIGATORIO**: Todo agente debe seguir este protocolo antes de crear o editar notas.

---

## Reglas Críticas (Kill-Switch)

### 1. Cero Emojis
- **PROHIBIDO** usar emojis en títulos de notas.
- **PROHIBIDO** usar emojis en cabeceras (`# H1`, `## H2`).
- **PROHIBIDO** usar emojis en nombres de carpetas.
- *Excepción*: Solo permitidos dentro del contenido si son semánticamente necesarios (ej: documentación de emojis), pero evítalos por defecto. Mantén un tono serio y profesional.

### 2. Regla de Oro de Edición
1. **PRIMERO** lee la nota con `notes.read`.
2. Para cambios puntuales usa `notes.patch` (reemplazos exactos) o `notes.update_frontmatter`; reserva `notes.replace` para reescribir la nota entera, y entonces el contenido debe ser el **ARCHIVO COMPLETO**.
3. **REEMPLAZA** el bloque YAML existente, no lo dupliques.
4. **NUNCA** elimines contenido existente accidentalmente.

### 3. Restricciones de Acceso
- No accedas a archivos en `.forbidden_paths` ni en los `private_paths` de `.agents/vault.yaml`.
- Respeta la privacidad de notas marcadas con `#privado`.

### 4. Diagramas en Mermaid
- **PROHIBIDO** usar diagramas ASCII art (cajas con `┌──┐`, `│`, etc.).
- **OBLIGATORIO** usar bloques ` ```mermaid ` para cualquier diagrama.
- Antes de crear diagramas, consultar la skill [[diagrama-arquitectura]] para sintaxis segura en Obsidian.
- Recordar: evitar `()` dentro de nodos `[]`, usar etiquetas en flechas para detalles.

### 5. Imágenes con Valor Semántico
- **OBLIGATORIO**: Todas las imágenes deben tener una descripción o caption explicativa.
- **Formato**: `![[imagen.png|Descripción detallada del contenido]]` o `![Descripción](imagen.png)`.
- **Propósito**: El sistema indexa estas descripciones para la búsqueda semántica. Una imagen sin caption es invisible para el conocimiento del vault.

### 6. Ortografía Correcta en Español
- **OBLIGATORIO**: Todo el contenido en español debe usar tildes, signos de puntuación y ortografía correctos.
- **PROHIBIDO** omitir tildes en palabras que las requieren, incluidos títulos, cabeceras, frontmatter y cuerpo de la nota.
- Palabras de uso frecuente que **siempre** llevan tilde y suelen olvidarse: *también, más, así, qué, cómo, dónde, cuándo, sí, él, está, análisis, índice, último, única, crítico, método, teórico, información, cognición, función, señal, solución, relación, acción, comprensión, elaboración, heurística, hipótesis, tálamo, sueño, después, también, además, través*.
- Los nombres propios en español también llevan tilde cuando corresponde (ej: *Briñol*).
- **Antes de guardar cualquier nota**, hacer una pasada mental verificando que las palabras esdrújulas, agudas y graves estén acentuadas correctamente.

### 7. Ciclo de Estados
- **OBLIGATORIO** usar el campo `status` en frontmatter para el estado de la nota.
- **PROHIBIDO** usar tags como estado (`#Archivo`, `#Borrador`, `#pendiente`, etc.).
- Valores válidos: `captura`, `en_proceso`, `completo`, `archivo`.
- Ciclo: `captura → en_proceso → completo → archivo`.

### 8. Tags solo para Temática
- Las tags son exclusivamente para temática y dominio de conocimiento.
- **PROHIBIDO** usar tags para representar estado o tipo de nota.
- Estado va en `status:` del frontmatter. Tipo va en `type:` del frontmatter.
- Consultar el Registro de Tags del Vault para tags canónicas.

### 9. Markdown sin Hard-Wrap
- **PROHIBIDO** cortar las líneas de prosa a mano a un ancho fijo (estilo commits de git o 80 columnas). En el editor de Obsidian esto se ve como estrofas de poema y dificulta la edición.
- **OBLIGATORIO** escribir cada párrafo en una sola línea lógica y dejar que Obsidian lo envuelva solo (soft wrap).
- Los saltos de línea solo separan párrafos, elementos de lista o bloques, nunca trocean una misma frase o párrafo.

---

## Protocolo Antes de Crear Notas

### Paso 1: Verificar Contexto del Vault
Ejecuta siempre primero `vault.context` (MCP `obsidian`). Te dará la estructura de carpetas, plantillas disponibles y convenciones actuales. El resumen operativo para agentes está en `AGENTS.md`, en la raíz del vault.

### Paso 2: Verificar Ubicación Correcta
- Usa `notes.suggest_location` para confirmar destino.
- Las carpetas de cada tipo de contenido están en la tabla «Dónde va cada cosa» de `AGENTS.md` y en `taxonomy.templates` de `.agents/vault.yaml`.

### Paso 3: Confirmar con el Usuario
**ANTES de crear cualquier nota**, comunica al usuario la ubicación propuesta y espera confirmación.

### Paso 4: Usar Frontmatter Real
- **NUNCA** inventes valores de frontmatter.
- **NUNCA** dejes placeholders (`2026-01-18`).
- **SIEMPRE** usa valores reales para `type`, `tags`, `created`.

---

## Tipos de Contenido Válidos

La lista que vale es `taxonomy.types` en `.agents/vault.yaml`: el MCP valida contra ella. Si añades un tipo, añádelo allí y, si tiene plantilla, también en `taxonomy.templates`. Escribe los tipos siempre con acentos.
