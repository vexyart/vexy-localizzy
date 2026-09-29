# this_file: tests/sourcefix/test_locations.py
"""Qt location filename inheritance differs for first and subsequent references."""

from vexy_localizzy.sourcefix.catalog import Catalog, rebase_locations


def test_locations_when_relative_then_inherit_first_filename(tmp_path):
    path = tmp_path / "en.ts"
    path.write_text("""<TS><context><name>X</name>
<message><location filename="a.cpp" line="+10"/><location filename="b.cpp" line="+20"/><source>A</source></message>
<message><location line="+3"/><source>B</source></message>
<message><location filename="b.cpp" line="-2"/><source>C</source></message>
</context></TS>""")
    catalog = Catalog(path)
    locations = list(catalog.locations().values())
    assert locations == [
        [(tmp_path / "a.cpp", 10), (tmp_path / "b.cpp", 20)],
        [(tmp_path / "a.cpp", 13)],
        [(tmp_path / "b.cpp", 18)],
    ]
    rebase_locations(catalog, {tmp_path / "a.cpp": [(1, 2, 4)]})
    changed = Catalog(path, catalog.render())
    assert list(changed.locations().values())[1] == [(tmp_path / "a.cpp", 17)]
    assert list(changed.locations().values())[2] == [(tmp_path / "b.cpp", 18)]


def test_locations_when_no_line_then_keep_file_reference(tmp_path):
    path = tmp_path / "en.ts"
    path.write_text(
        '<TS><context><name>X</name><message><location filename="a.cpp"/><source>A</source></message></context></TS>'
    )
    assert list(Catalog(path).locations().values()) == [[(tmp_path / "a.cpp", None)]]
