"""Build a platform-specific MCPB bundle with a local binary server."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess  # nosec B404
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = PROJECT_ROOT / "packaging" / "mcpb" / "manifest.template.json"
ENTRY_POINT = PROJECT_ROOT / "mcpb" / "server" / "obsidian_mcp_server.py"
BUNDLE_NAME = "obsidian-mcp-server"


def _platform_name() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "darwin"
    if system == "windows":
        return "win32"
    if system == "linux":
        return "linux"
    raise RuntimeError(f"Unsupported platform: {platform.system()}")


def _binary_name() -> str:
    if _platform_name() == "win32":
        return f"{BUNDLE_NAME}.exe"
    return BUNDLE_NAME


def _run(args: list[str]) -> None:
    subprocess.run(args, cwd=PROJECT_ROOT, check=True)  # nosec B603


def _read_project_version() -> str:
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    return str(pyproject["project"]["version"])


def _build_binary() -> Path:
    spec_path = PROJECT_ROOT / "build" / "pyinstaller"
    spec_path.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "uv",
            "run",
            "pyinstaller",
            "--clean",
            "--onefile",
            "--specpath",
            str(spec_path.relative_to(PROJECT_ROOT)),
            "--name",
            BUNDLE_NAME,
            str(ENTRY_POINT.relative_to(PROJECT_ROOT)),
        ]
    )
    binary_path = PROJECT_ROOT / "dist" / _binary_name()
    if not binary_path.exists():
        raise FileNotFoundError(f"PyInstaller did not create {binary_path}")
    return binary_path


def _release_artifact_path(version: str, platform_name: str) -> Path:
    filename = f"{BUNDLE_NAME}-{version}-{platform_name}.mcpb"
    return PROJECT_ROOT / "dist" / "mcpb" / filename


def _stage_bundle(binary_path: Path, version: str) -> Path:
    platform_name = _platform_name()
    binary_name = _binary_name()
    stage_path = PROJECT_ROOT / "build" / "mcpb" / platform_name
    server_path = stage_path / "server"

    if stage_path.exists():
        shutil.rmtree(stage_path)
    server_path.mkdir(parents=True)

    staged_binary = server_path / binary_name
    shutil.copy2(binary_path, staged_binary)
    staged_binary.chmod(staged_binary.stat().st_mode | 0o111)

    manifest = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    manifest["version"] = version
    manifest["compatibility"]["platforms"] = [platform_name]
    manifest["server"]["entry_point"] = f"server/{binary_name}"
    manifest["server"]["mcp_config"]["command"] = f"${{__dirname}}/server/{binary_name}"

    manifest_path = stage_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return stage_path


def _pack_bundle(stage_path: Path, version: str, platform_name: str) -> Path:
    stage_arg = str(stage_path.relative_to(PROJECT_ROOT))
    _run(["npx", "--yes", "@anthropic-ai/mcpb", "validate", stage_arg])
    _run(["npx", "--yes", "@anthropic-ai/mcpb", "pack", stage_arg])

    generated_artifact = PROJECT_ROOT / f"{stage_path.name}.mcpb"
    if not generated_artifact.exists():
        raise FileNotFoundError(f"MCPB pack did not create {generated_artifact}")

    release_artifact = _release_artifact_path(version, platform_name)
    release_artifact.parent.mkdir(parents=True, exist_ok=True)
    if release_artifact.exists():
        release_artifact.unlink()
    shutil.move(str(generated_artifact), release_artifact)
    return release_artifact


def main() -> None:
    """Build, validate, and pack the MCPB bundle for this platform."""
    version = _read_project_version()
    platform_name = _platform_name()
    binary_path = _build_binary()
    stage_path = _stage_bundle(binary_path, version)
    artifact = _pack_bundle(stage_path, version, platform_name)
    print(f"Built MCPB: {artifact}")


if __name__ == "__main__":
    main()
