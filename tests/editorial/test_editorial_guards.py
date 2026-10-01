# this_file: tests/editorial/test_editorial_guards.py
"""Shape, token and mnemonic guards: what a correction must keep from the source."""

from vexy_localizzy.editorial.guards import mnemonics, problem, safe, tokens


def test_safe_when_trailing_ellipsis_dropped_then_rejected():
    assert not safe("Ouvrir…", "Ouvrir", "Open…"), "… dropped"
    assert not safe("Ouvrir...", "Ouvrir", "Open..."), "... dropped"
    assert not safe("Ouvrir…", "Ouvrir"), "no source: compare with before"
    assert safe("Ouvrir…", "Ouvrir...", "Open…"), (
        "switching the ellipsis form keeps its presence"
    )


def test_safe_when_printf_argument_deleted_then_rejected():
    assert not safe("Zoom %.2f", "Zoom", "Zoom %.2f"), "%.2f deleted"
    assert not safe("%ld glyphes", "glyphes", "%ld glyphs"), "%ld deleted"
    assert not safe("%d fichiers", "%s fichiers", "%d files"), (
        "a changed conversion is a different argument"
    )
    assert not safe("Zoom %.2f", "Zoom"), "old candidates without source"


def test_safe_when_brace_or_double_brace_changed_then_rejected():
    assert not safe("Salut {{name}}", "Salut {name}", "Hi {{name}}"), "{{}} → {}"
    assert not safe("Salut {name}", "Salut", "Hi {name}"), "{name} deleted"


def test_safe_when_revision_compared_with_source_then_restoring_passes_and_defect_fails():
    assert safe("Ouvrir", "Ouvrir %1", "Open %1"), (
        "a fix that restores the source placeholder is accepted"
    )
    assert not safe("Ouvrir", "Ouvrir le fichier", "Open %1"), (
        "a revision that keeps a missing placeholder is refused"
    )


def test_safe_when_colon_whitespace_or_newline_changed_then_rejected():
    assert not safe("Nom :", "Nom", "Name:"), "trailing colon"
    assert not safe("Nom ", "Nom", "Name "), "trailing whitespace"
    assert not safe(" Nom", "Nom", " Name"), "leading whitespace"
    assert not safe("a\nb", "a b", "a\nb"), "newline"
    assert not safe("a\\nb", "a b", "a\\nb"), "literal \\n escape"
    assert not safe("Nom", "Nom :", "Name"), "a colon the source lacks"
    assert safe("Nom :", "Intitulé :", "Name:"), "a French colon is kept"
    assert safe("Nom :", "Intitulé：", "Name:"), "a full-width colon counts"


def test_safe_when_plural_list_empty_or_wrong_length_then_rejected():
    assert not safe(["%n a", "%n b"], [], "%n x"), "empty list"
    assert not safe(["%n a", "%n b"], ["%n a"], "%n x"), "one form short"
    assert safe(["%n a", "%n b"], ["%n c", "%n d"], "%n x"), "same length passes"


def test_problem_when_one_count_form_spells_out_the_number_then_safe():
    before = ["%n plik", "%n pliki", "%n plików"]
    spelled = ["Jeden plik", "%n pliki", "%n plików"]
    source, singular = "%n file(s)", frozenset({0})
    assert problem(before, spelled, source) == "shape", "strict without the rule"
    assert problem(before, spelled, source, count_optional=singular) is None, (
        "the form that one count selects may omit %n"
    )
    assert problem(spelled, before, source, count_optional=singular) is None, (
        "putting the count back is fine too"
    )
    ranged = ["%n plik", "pliki", "%n plików"]
    assert problem(before, ranged, source, count_optional=singular) == "shape", (
        "a form of several counts must keep %n"
    )


def test_problem_when_one_count_form_changes_another_token_then_shape():
    source, singular = "%n file(s) in %1:", frozenset({0})
    before = ["%n plik w %1:", "%n pliki w %1:"]
    assert (
        problem(
            before, ["Jeden plik w %1:", before[1]], source, count_optional=singular
        )
        is None
    )
    for revised in (
        "Jeden plik:",
        "Jeden plik w %1",
        "Jeden plik w %1 %2:",
        "%n %n plik w %1:",
    ):
        assert (
            problem(before, [revised, before[1]], source, count_optional=singular)
            == "shape"
        ), revised
    assert (
        problem("%n plik", "Jeden plik", "%n file(s)", count_optional=singular)
        == "shape"
    ), "a scalar message never gets the exemption"


def test_problem_when_plural_list_wrong_length_then_reason_is_plural_forms():
    assert problem(["%n a", "%n b"], ["%n a"], "%n x") == "plural_forms", "length"
    assert problem(["%n a", "%n b"], "%n a", "%n x") == "plural_forms", "list → text"
    assert problem("a", ["a"], "a") == "plural_forms", "text → list"


def test_problem_when_each_rule_broken_then_reason_names_it():
    assert problem("Nom", "  ", "Name") == "empty", "blank revision"
    assert problem("Nom", "Nom :", "Name") == "shape", "punctuation"
    assert problem("&Nom", "Nom", "&Name") == "mnemonic", "accelerator dropped"
    assert problem("&Nom", "&Intitulé", "&Name") is None, "a safe rewording"


def test_problem_when_markup_relaxed_then_only_tags_and_mnemonics_relaxed():
    assert problem("<b>Nom</b>", "<i>Nom</i>", "<b>Name</b>", markup=True) is None, (
        "a markup repair may change tags"
    )
    assert problem("<b>Nom</b>:", "<i>Nom</i>", "<b>Name</b>:", markup=True) == (
        "shape"
    ), "a lost colon is refused even for markup"
    assert problem("<b>%1</b>", "<i>x</i>", "<b>%1</b>", markup=True) == "shape", (
        "a lost placeholder is refused even for markup"
    )
    assert problem("<b>a</b>\nb", "<i>a</i> b", "<b>a</b>\nb", markup=True) == (
        "shape"
    ), "a lost newline is refused even for markup"


def test_mnemonics_when_rich_text_entities_then_not_counted():
    assert mnemonics("<b>A &amp; B</b>") == 0, "&amp; in rich text is literal"
    assert mnemonics("<p>A&nbsp;B&#160;C&#xA0;</p>") == 0, "named and numeric entities"
    assert mnemonics("<b>&Save &amp; close</b>") == 1, "a real accelerator still counts"
    assert mnemonics("A &amp; B") == 1, "plain text: &amp; underlines the a"
    assert mnemonics("Save && &Close") == 1, "&& is a literal ampersand"


def test_safe_when_rich_entity_becomes_bare_ampersand_then_rejected():
    assert not safe("<b>A &amp; B</b>", "<b>A & B</b>", "<b>A &amp; B</b>"), (
        "a bare & in rich text adds an accelerator"
    )
    assert safe("<b>A &amp; B</b>", "<b>A&nbsp;&amp; B</b>", "<b>A &amp; B</b>"), (
        "adding an entity adds no accelerator"
    )


def test_tokens_when_tags_excluded_then_placeholders_only():
    assert tokens("<b>%1</b> {n}", tags=False) == ["%1", "{n}"], "tags dropped"
    assert tokens("<b>%1</b>") == ["%1", "</b>", "<b>"], "tags kept by default"
