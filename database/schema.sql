CREATE TABLE variants (
    id INTEGER PRIMARY KEY,
    chrom TEXT,
    position INTEGER,
    ref TEXT,
    alt TEXT,
    gene TEXT,
    clinical_significance TEXT,
    disease TEXT,
    evidence TEXT
);
