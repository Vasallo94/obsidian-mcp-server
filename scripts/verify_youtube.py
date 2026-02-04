from obsidian_mcp.tools.youtube_logic import get_transcript_text


def test_transcript_fetch() -> None:
    print("\nTesting transcript fetch (Auto Language)...")
    # "Me at the zoo" id: jNQXAC9IVRw. English audio.
    # Manual English subs might exist or auto-gen. Usually has manual "en" or auto.

    # We call it WITHOUT specifying language (defaults to None, so Auto).
    # expected: Should return English text, or maybe Spanish if I force it?
    # Logic is: Prioritize Manual.

    video_id = "jNQXAC9IVRw"
    url = f"https://www.youtube.com/watch?v={video_id}"

    print(f"Fetching transcript for {url} [Auto Mode]...")
    result = get_transcript_text(url)

    if not result.success or not result.data:
        print(f"FAILED: {result.error}")
        return

    text = result.data
    print("Result Snippet:", text[:300].replace("\n", " "))

    if "Idioma:" in text:
        print("MetaData Found.")
    else:
        print("FAILED: Metadata not found in response.")

    if "elephants" in text or "trunks" in text:
        print("Content Check: PASSED (Found English content)")
    else:
        print(
            "Content Check: WARNING (English content not found, "
            "maybe returned Spanish translation?)"
        )

    # Test 2: Force Spanish (if available or translatable)
    # My code currently fails if not found unless I implemented translation logic fully.
    # My code has `pass` for translation fallback in `if language:`.
    # Let's see if "es" exists for this video.
    print(f"\nFetching transcript for {url} [Language='es']...")
    result_es = get_transcript_text(url, language="es")
    if result_es.success and result_es.data:
        print("Result snippet (ES):", result_es.data[:300].replace("\n", " "))
    else:
        print(f"ES fetch failed: {result_es.error}")

    # "Me at the zoo" typically doesn't have manual Spanish.
    # So my code might fail or return error.


if __name__ == "__main__":
    try:
        test_transcript_fetch()
    except Exception as e:
        print(f"Execution failed with exception: {e}")
