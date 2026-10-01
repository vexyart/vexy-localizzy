# this_file: src/vexy_localizzy/cli/checks.py
"""``localizzy`` commands that inspect or derive catalogs: qa, pseudo, vocab, doctor, init.

Findings are data: a command prints them and exits 1 when a blocking one is
present. Exit 2 is a usage error and exit 3 a missing optional dependency.
"""

import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from vexy_localizzy.cli._args import csv_strings
from vexy_localizzy.external import MissingDependencyError

EXIT_FINDINGS, EXIT_USAGE, EXIT_DEPENDENCY = 1, 2, 3
AUTO = "auto"
SUFFIX_FORMATS = {
    ".ts": "ts",
    ".json": "json",
    ".po": "po",
    ".xlf": "xliff",
    ".xliff": "xliff",
    ".xml": "android",
}


def _fail(message: str, code: int) -> SystemExit:
    print(message, file=sys.stderr)
    return SystemExit(code)


def _refuse_overwrite(out: str | None, *inputs: str) -> None:
    """An output that resolves to an input would destroy it: a usage error."""
    if out and Path(out).resolve() in {Path(path).resolve() for path in inputs}:
        raise _fail(f"--out would overwrite an input: {out}", EXIT_USAGE)


def _layer_findings(loaded, layers: list[str], options: dict) -> list:
    """Run the named optional layers; an unknown name is a usage error."""
    from vexy_localizzy.qa import layers as qa_layers

    if unknown := set(layers) - set(qa_layers.LAYERS):
        raise _fail(f"--layers: unknown layer {sorted(unknown)}", EXIT_USAGE)
    findings = []
    if "pofilter" in layers:
        findings += qa_layers.run_pofilter(loaded)
    if "qe" in layers:
        findings += qa_layers.run_qe(loaded, threshold=options["qe_threshold"])
    if "judge" in layers:
        api_key = os.environ.get(options["api_key_env"], "")
        if not (options["endpoint"] and options["model"] and api_key.strip()):
            raise _fail(
                "The judge layer needs --endpoint, --model and the API key variable",
                EXIT_USAGE,
            )
        findings += qa_layers.run_judge(
            loaded,
            model=options["model"],
            endpoint=options["endpoint"],
            api_key=api_key,
            sample=options["judge_sample"],
            mqm_threshold=options["mqm_threshold"],
            brand_terms=csv_strings(options["brand_terms"]),
            ignore_keys=csv_strings(options["ignore_keys"]),
        )
    return findings


def qa(
    catalog: str,
    fail_on: str = "major",
    plural_forms: str | None = None,
    layers: str | None = None,
    format: str | None = None,
    out: str | None = None,
    endpoint: str | None = None,
    model: str | None = None,
    api_key_env: str = "OPENAI_API_KEY",
    judge_sample: float = 0.1,
    mqm_threshold: int = 80,
    qe_threshold: float = 0.7,
    brand_terms: str | None = None,
    ignore_keys: str | None = None,
) -> dict | None:
    """Run the deterministic content checks on a catalog; exit 1 on blocking findings.

    --plural-forms 0,1,2 names the required native forms; ``auto`` derives them
    from the target language. --layers pofilter,qe,judge adds the optional
    layers (the judge needs --endpoint and --model). --format table, json or
    sarif renders the findings, to --out when given; without --format the
    result is one JSON object.
    """
    from vexy_localizzy import report
    from vexy_localizzy.conversion import load_any
    from vexy_localizzy.qa.catalog import check_catalog
    from vexy_localizzy.qa.layers import native_plural_forms
    from vexy_localizzy.qa.text import TextPolicy

    if fail_on not in report.SEVERITY_RANK:
        raise _fail(
            f"--fail_on must be one of {', '.join(report.SEVERITY_RANK)}", EXIT_USAGE
        )
    if format is not None and format not in report.FORMATS:
        raise _fail(f"--format must be one of {', '.join(report.FORMATS)}", EXIT_USAGE)
    _refuse_overwrite(out, catalog)
    loaded = load_any(catalog)
    try:
        required = (
            native_plural_forms(loaded)
            if plural_forms == AUTO
            else tuple(csv_strings(plural_forms)) or None
        )
        findings = check_catalog(
            loaded, policy=TextPolicy(), required_plural_forms=required
        )
        options = {
            "endpoint": endpoint,
            "model": model,
            "api_key_env": api_key_env,
            "judge_sample": judge_sample,
            "mqm_threshold": mqm_threshold,
            "qe_threshold": qe_threshold,
            "brand_terms": brand_terms,
            "ignore_keys": ignore_keys,
        }
        findings += _layer_findings(loaded, csv_strings(layers), options)
    except MissingDependencyError as error:
        raise _fail(str(error), EXIT_DEPENDENCY) from error
    except (ValueError, RuntimeError) as error:
        raise _fail(str(error), EXIT_USAGE) from error
    blocking = report.blocking(findings, fail_on)
    if format is not None:
        # A catalog finding has no line; the file is the location SARIF consumers need.
        located = [
            f if f.location else f.model_copy(update={"location": str(catalog)})
            for f in findings
        ]
        report.emit(located, format, out, title=f"qa {Path(catalog).name}")
        if blocking:
            raise SystemExit(EXIT_FINDINGS)
        return None
    result = {
        "catalog": str(catalog),
        "units": len(loaded.units),
        "findings": [f.model_dump() for f in findings],
        "blocking": len(blocking),
    }
    if blocking:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        raise SystemExit(EXIT_FINDINGS)
    return result


def pseudo(
    catalog: str,
    out: str,
    expansion: float = 0.4,
    mode: str = "accent",
    allow_loss: bool = False,
) -> dict:
    """Write a pseudo-localized copy of CATALOG to OUT (format from OUT's suffix).

    --mode accent wraps and accents the text and pads it by --expansion of its
    length; bracket uses plain brackets; rtl wraps the unchanged text in
    right-to-left marks. Placeholders, tags and accelerators are never changed.
    """
    from vexy_localizzy.conversion import ConversionLoss, convert_catalog, load_any
    from vexy_localizzy.pseudo import pseudo_catalog

    target = SUFFIX_FORMATS.get(Path(out).suffix.lower())
    if target is None:
        raise _fail(f"Unsupported output suffix: {Path(out).suffix}", EXIT_USAGE)
    _refuse_overwrite(out, catalog)
    try:
        result = pseudo_catalog(load_any(catalog), expansion=expansion, mode=mode)
        convert_catalog(result, target, out, allow_loss=allow_loss)
    except (ConversionLoss, ValueError) as error:
        raise _fail(str(error), EXIT_USAGE) from error
    return {"output": str(out), "units": len(result.units), "mode": mode}


def _candidate(path: str, load_any):
    """A flat ``{key: translation}`` JSON file as a mapping; anything else as a catalog."""
    if Path(path).suffix.lower() == ".json":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(data, dict) and all(isinstance(v, str) for v in data.values()):
            return data
    return load_any(path)


def vocab(
    action: str,
    path: str,
    locale: str | None = None,
    out: str | None = None,
    format: str = "table",
    candidate: str | None = None,
    min_exact: float | None = None,
    flat: bool = False,
) -> dict | None:
    """Inspect a vocabulary corpus at PATH: stats, list, validate, export or compare.

    ``validate`` exits 1 when an entry lacks context or an ICU plural lacks
    ``other``. ``export`` writes canonical catalog JSON to --out; --locale
    selects the target language of ``list`` and ``export``. --flat exports a flat
    {key: text} JSON file, the input of ``translate_json``. ``compare`` scores
    the --candidate (a catalog, or a flat {key: translation} JSON file) against
    the --locale references and exits 1 when the exact-match rate is below
    --min-exact.
    """
    from vexy_localizzy import report
    from vexy_localizzy import vocab as corpus

    if action == "stats":
        return asdict(corpus.stats(path))
    if action == "list":
        for unit in corpus.load(path, locale=locale).units:
            print(f"{unit.key}\t{unit.target or unit.source}\t{unit.context}")
        return None
    if action == "validate":
        if format not in report.FORMATS:
            raise _fail(
                f"--format must be one of {', '.join(report.FORMATS)}", EXIT_USAGE
            )
        findings = corpus.validate(path)
        report.emit(findings, format, out, title="vocab validate")
        if findings:
            raise SystemExit(EXIT_FINDINGS)
        return None
    if action == "export":
        if not out:
            raise _fail("vocab export needs --out", EXIT_USAGE)
        _refuse_overwrite(out, path)
        if flat:
            mapping = corpus.flat(path, locale=locale)
            text = json.dumps(mapping, ensure_ascii=False, indent=2) + "\n"
            Path(out).write_text(text, encoding="utf-8")
            return {"output": out, "units": len(mapping)}
        return {
            "output": out,
            "units": len(corpus.export(out, path, locale=locale).units),
        }
    if action == "compare":
        if not (candidate and locale):
            raise _fail("vocab compare needs --candidate and --locale", EXIT_USAGE)
        from vexy_localizzy.conversion import load_any

        result = corpus.compare(path, _candidate(candidate, load_any), locale)
        if min_exact is not None and result["exact_rate"] < min_exact:
            print(json.dumps(result, ensure_ascii=False, indent=1))
            raise SystemExit(EXIT_FINDINGS)
        return result
    raise _fail(f"unknown vocab action: {action}", EXIT_USAGE)


def doctor() -> None:
    """Report platform, Python, external tools and optional extras; install nothing."""
    from vexy_localizzy import doctor as environment

    print(environment.render(environment.run()))


def init(root: str = ".", force: bool = False) -> dict:
    """Write a starter localizzy.toml under ROOT; an existing file is kept unless --force."""
    from vexy_localizzy.project import init as scaffold

    return dict(scaffold(root, force=force))
