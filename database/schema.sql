CREATE TABLE IF NOT EXISTS genes (
id INTEGER PRIMARY KEY AUTOINCREMENT,
symbol TEXT UNIQUE NOT NULL,
ensembl_id TEXT,
name TEXT,
chromosome TEXT,
description TEXT,
inheritance_pattern TEXT
);
CREATE TABLE IF NOT EXISTS diseases (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT UNIQUE NOT NULL,
omim_id TEXT,
mondo_id TEXT,
icd10 TEXT,
description TEXT,
severity TEXT,
age_of_onset TEXT,
inheritance TEXT
);
CREATE TABLE IF NOT EXISTS variants (
id INTEGER PRIMARY KEY AUTOINCREMENT,
chromosome TEXT NOT NULL,
position INTEGER NOT NULL,
reference TEXT NOT NULL,
alternate TEXT NOT NULL,
gene_id INTEGER,
hgvs_genomic TEXT,
hgvs_coding TEXT,
hgvs_protein TEXT,
clinvar_significance TEXT,
clinvar_review_status TEXT,
dbsnp_id TEXT,
clinvar_variation_id TEXT,
raw_info TEXT,
source TEXT DEFAULT 'clinvar',
imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (gene_id) REFERENCES genes(id)
);
CREATE TABLE IF NOT EXISTS variant_disease (
variant_id INTEGER NOT NULL,
disease_id INTEGER NOT NULL,
significance TEXT,
evidence_level TEXT,
penetrance REAL,
mechanism TEXT,
PRIMARY KEY (variant_id, disease_id),
FOREIGN KEY (variant_id) REFERENCES variants(id),
FOREIGN KEY (disease_id) REFERENCES diseases(id)
);
CREATE TABLE IF NOT EXISTS phenotypes (
id INTEGER PRIMARY KEY AUTOINCREMENT,
hpo_id TEXT UNIQUE,
name TEXT NOT NULL,
category TEXT
);
CREATE TABLE IF NOT EXISTS disease_phenotype (
disease_id INTEGER NOT NULL,
phenotype_id INTEGER NOT NULL,
frequency TEXT,
evidence TEXT,
PRIMARY KEY (disease_id, phenotype_id),
FOREIGN KEY (disease_id) REFERENCES diseases(id),
FOREIGN KEY (phenotype_id) REFERENCES phenotypes(id)
);
CREATE TABLE IF NOT EXISTS medications (
id INTEGER PRIMARY KEY AUTOINCREMENT,
drug_name TEXT NOT NULL,
drug_class TEXT,
rxnorm_id TEXT,
description TEXT
);
CREATE TABLE IF NOT EXISTS variant_medication (
variant_id INTEGER NOT NULL,
medication_id INTEGER NOT NULL,
effect TEXT,
recommendation TEXT,
guideline_source TEXT,
PRIMARY KEY (variant_id, medication_id),
FOREIGN KEY (variant_id) REFERENCES variants(id),
FOREIGN KEY (medication_id) REFERENCES medications(id)
);
CREATE TABLE IF NOT EXISTS user_genotypes (
id INTEGER PRIMARY KEY AUTOINCREMENT,
sample_name TEXT,
variant_id INTEGER NOT NULL,
genotype TEXT,
zygosity TEXT,
quality REAL,
imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (variant_id) REFERENCES variants(id)
);