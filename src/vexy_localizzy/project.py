# this_file: src/vexy_localizzy/project.py
"""Project configuration: one ``localizzy.toml`` holds a project's paths and tags.

The general commands take every path as an argument. A project that runs them
weekly writes its catalog layout, memories, language tags and engine settings
once, and then names a language code: ``localizzy project upgrade de``. The
file is found from the working directory upward and parsed once into frozen
records; unknown keys are an error, not a silent default. Relative paths are
resolved against the directory of the file. Referenced by ``cli.project`` and
``cli.qt``.
"""

import tomllib
from pathlib import Path

from pydantic import Field, ValidationError

from vexy_localizzy.catalog import Record

CONFIG_FILENAME = "localizzy.toml"
CODE_FIELD = "{code}"


class ConfigError(ValueError):
    """The project file cannot be read as a configuration; the message is one line."""


class SourceConfig(Record):
    language: str = "en"
    locales: list[str] = Field(default_factory=list)


class QtConfig(Record):
    """Qt sources for ``qt scan`` and ``qt extract``: directories or ``.pro`` files."""

    sources: list[str] = Field(default_factory=list)
    out_dir: str = "i18n/fresh"  # never the approved catalogs: upgrade ports onto these
    prefix: str = "app"


class CatalogsConfig(Record):
    """Where the project's catalogs live; ``{code}`` is the language code."""

    dir: str = "i18n"
    pattern: str = "app_{code}.ts"
    fresh_dir: str = "i18n/fresh"
    retired_dir: str = "i18n/retired"
    report_dir: str = "i18n/upgrade"


class MemoriesConfig(Record):
    """Translation memories, resolved per language code."""

    dir: str = "i18n/memories"
    direct: list[str] = Field(default_factory=lambda: ["{code}-ui.tmx"])
    glossary: list[str] = Field(default_factory=lambda: ["{code}-core.tmx"])
    glossary_statuses: list[str] = Field(
        default_factory=lambda: ["approved", "do-not-translate"]
    )


class LanguageConfig(Record):
    """Per-language tags: the catalog's target language and the memories' ``xml:lang``."""

    catalog: str
    memory: str | None = None


class TranslateConfig(Record):
    temperature: float = Field(default=0.2, ge=0, le=2, allow_inf_nan=False)
    endpoint: str = Field(default="https://api.openai.com/v1", min_length=1)
    api_key_env: str = Field(default="OPENAI_API_KEY", min_length=1)
    cache_path: str = Field(default=".localizzy/translation-cache.sqlite", min_length=1)
    fallback_models: list[str] = Field(default_factory=list)
    timeout: float = Field(default=300, gt=0)
    style_file: str | None = None


class Config(Record):
    """The resolved, immutable project configuration."""

    source: SourceConfig = Field(default_factory=SourceConfig)
    qt: QtConfig = Field(default_factory=QtConfig)
    catalogs: CatalogsConfig = Field(default_factory=CatalogsConfig)
    memories: MemoriesConfig = Field(default_factory=MemoriesConfig)
    languages: dict[str, LanguageConfig] = Field(default_factory=dict)
    translate: TranslateConfig = Field(default_factory=TranslateConfig)
    config_path: str | None = None  # the localizzy.toml that was loaded, if any

    def anchor(self) -> Path:
        """The directory that relative paths in the file are resolved against."""
        if self.config_path:
            return Path(self.config_path).resolve().parent
        return Path.cwd()

    def resolve(self, path: str) -> Path:
        return (self.anchor() / path).absolute()

    def catalog_name(self, code: str) -> str:
        if CODE_FIELD not in self.catalogs.pattern:
            raise ValueError(f"[catalogs].pattern must contain {CODE_FIELD}")
        return self.catalogs.pattern.format(code=code)

    def catalog_path(self, code: str, *, fresh: bool = False) -> Path:
        directory = self.catalogs.fresh_dir if fresh else self.catalogs.dir
        return self.resolve(directory) / self.catalog_name(code)

    def language(self, code: str) -> LanguageConfig:
        """The tags for ``code``; a language absent from ``[languages]`` uses the code."""
        return self.languages.get(code) or LanguageConfig(catalog=code)

    def memory_candidates(self, code: str) -> dict[str, list[Path]]:
        """Configured direct and glossary memory paths for ``code``, existing or not."""
        root = self.resolve(self.memories.dir)
        return {
            kind: [root / name.format(code=code) for name in names]
            for kind, names in (
                ("direct", self.memories.direct),
                ("glossary", self.memories.glossary),
            )
        }

    def qt_sources(self) -> list[Path]:
        return [(self.anchor() / path).resolve() for path in self.qt.sources]


def discover_config(start: Path | None = None) -> Path | None:
    """Find ``localizzy.toml`` from ``start`` (or the working directory) upward."""
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def load_config(
    explicit: str | Path | None = None, *, start: Path | None = None
) -> Config:
    """Defaults, then the explicit or discovered ``localizzy.toml``.

    An explicit path that does not exist raises FileNotFoundError; with no file
    at all the built-in defaults are returned.
    """
    if explicit is not None:
        path: Path | None = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(f"config file not found: {path}")
    else:
        path = discover_config(start)
    if path is None:
        return Config()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        data["config_path"] = str(path.resolve())
        return Config.model_validate(data)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path}: {error}") from error
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
        raise ConfigError(f"{path}: {problems}") from error


TEMPLATE = """\
# localizzy project configuration. Paths are relative to this file.

[source]
language = "en"
locales = ["de", "fr"]

[qt]
# Qt source directories or .pro files for `localizzy qt scan` and `qt extract`.
sources = ["src"]
out_dir = "i18n/fresh"  # fresh lupdate output; `project upgrade` ports onto it
prefix = "app"

[catalogs]
# {code} is the language code given on the command line.
dir = "i18n"
pattern = "app_{code}.ts"
fresh_dir = "i18n/fresh"      # where `lupdate` writes the current strings
retired_dir = "i18n/retired"  # translations an upgrade could not carry over
report_dir = "i18n/upgrade"

[memories]
dir = "i18n/memories"
direct = ["{code}-ui.tmx"]      # literal matches from the reviewed catalog
glossary = ["{code}-core.tmx"]  # term decisions
glossary_statuses = ["approved", "do-not-translate"]

# Tags that differ from the code: the catalog language and the memory language.
# [languages.es]
# catalog = "es_MX"
# memory = "es-419"

[translate]
endpoint = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
cache_path = ".localizzy/translation-cache.sqlite"
fallback_models = []
temperature = 0.2
timeout = 300
"""


def init(root: str | Path = ".", *, force: bool = False) -> list[tuple[str, str]]:
    """Write a starter ``localizzy.toml`` under ``root``.

    Returns ``(relative path, action)`` pairs; an existing file is ``skipped``
    unless ``force`` is set.
    """
    path = Path(root) / CONFIG_FILENAME
    if path.exists() and not force:
        return [(CONFIG_FILENAME, "skipped")]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE, encoding="utf-8")
    return [(CONFIG_FILENAME, "created")]
