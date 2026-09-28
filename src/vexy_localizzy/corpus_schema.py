# this_file: src/vexy_localizzy/corpus_schema.py
"""SQLite schema and deterministic independent-family voting queries."""

SCHEMA_VERSION = 2
APPLICATION_ID = 0x4C5A5A59
SCHEMA = """
CREATE TABLE families (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
 weight INTEGER NOT NULL CHECK(weight > 0)
);
CREATE TABLE sources (
 id INTEGER PRIMARY KEY, path TEXT NOT NULL, sha256 TEXT NOT NULL, snapshot TEXT NOT NULL,
 family_id INTEGER NOT NULL REFERENCES families,
 policy TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('importing','complete','failed')),
 active INTEGER NOT NULL DEFAULT 0 CHECK(active IN (0,1)),
 progress INTEGER NOT NULL DEFAULT 0, error TEXT, error_ordinal INTEGER,
 UNIQUE(path, sha256, policy)
);
CREATE TABLE entries (
 id INTEGER PRIMARY KEY, source TEXT NOT NULL, source_xml TEXT NOT NULL DEFAULT '',
 UNIQUE(source, source_xml)
);
CREATE TABLE candidates (
 id INTEGER PRIMARY KEY, entry_id INTEGER NOT NULL REFERENCES entries,
 locale TEXT NOT NULL, target TEXT NOT NULL, target_xml TEXT NOT NULL DEFAULT '',
 UNIQUE(entry_id, locale, target, target_xml)
);
CREATE TABLE occurrences (
 source_id INTEGER NOT NULL REFERENCES sources,
 ordinal INTEGER NOT NULL, candidate_id INTEGER NOT NULL REFERENCES candidates,
 PRIMARY KEY(source_id, ordinal, candidate_id)
) WITHOUT ROWID;
CREATE INDEX occurrence_candidate ON occurrences(candidate_id, source_id);
CREATE TABLE origins (
 id INTEGER PRIMARY KEY, path TEXT NOT NULL, sha256 TEXT NOT NULL, snapshot TEXT NOT NULL,
 UNIQUE(path, sha256)
);
CREATE TABLE lineage (
 source_id INTEGER NOT NULL REFERENCES sources, ordinal INTEGER NOT NULL,
 candidate_id INTEGER NOT NULL REFERENCES candidates,
 origin_id INTEGER NOT NULL REFERENCES origins, origin_ordinal INTEGER NOT NULL,
 family_id INTEGER NOT NULL REFERENCES families,
 PRIMARY KEY(source_id, ordinal, candidate_id, origin_id, origin_ordinal, family_id),
 FOREIGN KEY(source_id, ordinal, candidate_id) REFERENCES occurrences
) WITHOUT ROWID;
CREATE INDEX lineage_candidate ON lineage(candidate_id, source_id);
CREATE TABLE exclusions (
 source_id INTEGER NOT NULL REFERENCES sources, ordinal INTEGER NOT NULL,
 reason TEXT NOT NULL, PRIMARY KEY(source_id, ordinal)
) WITHOUT ROWID;
CREATE VIEW scores AS
 SELECT candidate_id, SUM(weight) AS score, MAX(weight) AS max_weight
 FROM (
   SELECT DISTINCT o.candidate_id, f.id AS family_id, f.weight
   FROM lineage o JOIN sources s ON s.id=o.source_id
   JOIN families f ON f.id=o.family_id
   WHERE s.active=1 AND s.status='complete'
 ) GROUP BY candidate_id;
"""

WINNERS = """
WITH ranked AS (
 SELECT c.id AS candidate_id, c.entry_id, e.source, e.source_xml, c.locale, c.target, c.target_xml,
        s.score, s.max_weight,
        ROW_NUMBER() OVER (
          PARTITION BY c.entry_id,c.locale
          ORDER BY s.score DESC,s.max_weight DESC,c.target ASC,c.target_xml ASC
        ) AS rank,
        COUNT(*) OVER (
          PARTITION BY c.entry_id,c.locale,s.score
        ) > 1 AS tied
 FROM candidates c JOIN entries e ON e.id=c.entry_id
 JOIN scores s ON s.candidate_id=c.id
)
SELECT candidate_id,entry_id,source,source_xml,locale,target,target_xml,score,max_weight,tied
FROM ranked WHERE rank=1 ORDER BY source,locale
"""
