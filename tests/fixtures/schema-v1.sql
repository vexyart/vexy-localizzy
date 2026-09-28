-- this_file: tests/fixtures/schema-v1.sql

CREATE TABLE families (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
 weight INTEGER NOT NULL CHECK(weight > 0)
);
CREATE TABLE sources (
 id INTEGER PRIMARY KEY, path TEXT NOT NULL, sha256 TEXT NOT NULL, snapshot TEXT NOT NULL,
 family_id INTEGER NOT NULL REFERENCES families,
 status TEXT NOT NULL CHECK(status IN ('importing','complete','failed')),
 active INTEGER NOT NULL DEFAULT 0 CHECK(active IN (0,1)),
 progress INTEGER NOT NULL DEFAULT 0, error TEXT, error_ordinal INTEGER,
 UNIQUE(path, sha256)
);
CREATE TABLE entries (
 id INTEGER PRIMARY KEY, source TEXT NOT NULL UNIQUE
);
CREATE TABLE candidates (
 id INTEGER PRIMARY KEY, entry_id INTEGER NOT NULL REFERENCES entries,
 locale TEXT NOT NULL, target TEXT NOT NULL,
 UNIQUE(entry_id, locale, target)
);
CREATE TABLE occurrences (
 source_id INTEGER NOT NULL REFERENCES sources,
 ordinal INTEGER NOT NULL, candidate_id INTEGER NOT NULL REFERENCES candidates,
 PRIMARY KEY(source_id, ordinal, candidate_id)
) WITHOUT ROWID;
CREATE INDEX occurrence_candidate ON occurrences(candidate_id, source_id);
CREATE TABLE exclusions (
 source_id INTEGER NOT NULL REFERENCES sources, ordinal INTEGER NOT NULL,
 reason TEXT NOT NULL, PRIMARY KEY(source_id, ordinal)
) WITHOUT ROWID;
CREATE VIEW scores AS
 SELECT candidate_id, SUM(weight) AS score, MAX(weight) AS max_weight
 FROM (
   SELECT DISTINCT o.candidate_id, f.id AS family_id, f.weight
   FROM occurrences o JOIN sources s ON s.id=o.source_id
   JOIN families f ON f.id=s.family_id
   WHERE s.active=1 AND s.status='complete'
 ) GROUP BY candidate_id;
