# this_file: src/vexy_localizzy/extract/__init__.py
"""Foreign resources to TMX: the strict single-file extractor and the legacy converters.

``single`` is the strict extractor behind ``localizzy tm extract``; the
``*_resources`` and ``legacy_pairs`` modules parse the formats it accepts. The
legacy tree converters (``ts2tmx``, ``po2tmx``, ``lproj``, ``adobe``, ``oss``,
``names``) came from earlier converter scripts and keep their historical selection, language and
naming policy; see ``legacy_lang`` for the region-shortening rules. Submodules
are imported on demand because some need the optional ``sources`` extra.
"""
