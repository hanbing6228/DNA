# DNA Personal Genome Analyzer - Engine v2

**Command-line pipeline** for analyzing personal genome VCF files.

## Features

- ✅ **VCF / VCF.GZ** parsing
- ✅ **SnpEff ANN** annotation extraction (gene, impact, HGVS)
- ✅ **ClinVar** clinical significance parsing
- ✅ **Evidence scoring** (impact + ClinVar + review status)
- ✅ **Priority classification** (CRITICAL / HIGH / MODERATE / LOW)
- ✅ **Human-readable interpretations** with recommendations
- ✅ **HTML + JSON** report generation
- ✅ **Zero external dependencies** (pure Python standard library)

## Quick Start

```bash
# Analyze your VCF
python analyze.py path/to/your/clinical_ready.vcf.gz

# Output saved to reports/
#   report.json  - structured data
#   report.html  - human-readable report

# Process only first 1000 variants (for testing)
python analyze.py clinical_ready.vcf.gz --max-variants 1000

# Lower threshold to see more findings
python analyze.py clinical_ready.vcf.gz --min-score 2
```

## Pipeline Architecture

```
VCF File
  ↓
parse_vcf()
  ↓
For each variant:
  ├─ ANNParser.parse()         → gene, impact, HGVS
  ├─ ClinVarParser.parse()     → significance, disease
  ├─ EvidenceScorer.score()    → priority score
  └─ VariantInterpreter.interpret() → recommendations
  ↓
ReportGenerator
  ├─ report.json
  └─ report.html
```

## Scoring System

| Factor | Weight |
|---|---|
| HIGH impact | +10 |
| MODERATE impact | +5 |
| Pathogenic (ClinVar) | +10 |
| Likely pathogenic | +8 |
| Risk factor | +6 |
| Drug response | +7 |
| Expert panel review | +4 |
| Multiple submitters | +3 |

**Priority thresholds:**
- CRITICAL: ≥15
- HIGH: ≥10
- MODERATE: ≥5
- LOW: >0

## Output Example

```
📁 Loading: clinical_ready.vcf.gz
⏳ Parsing VCF...
✅ Parsed 93,525 variants
🔬 Analyzing all variants...

📊 Results:
   Total variants: 93,525
   Reported findings: 12
   HIGH: 3
   MODERATE: 9

🔴 Top findings:
   PRSS1 | pathogenic | Hereditary pancreatitis
   BRCA1 | pathogenic | Hereditary breast-ovarian cancer
   CFTR | pathogenic | Cystic fibrosis

💾 JSON report: reports/report.json
💾 HTML report: reports/report.html
```

## Report Preview

The HTML report includes:
- Summary statistics (Critical / High / Moderate / Low)
- Detailed variant cards with gene, HGVS, disease
- Clinical significance badges
- Personalized recommendations
- Evidence scoring breakdown

## Roadmap

- [ ] PharmGKB drug response integration
- [ ] Polygenic Risk Score (PRS) calculation
- [ ] Family mode (inheritance tracking)
- [ ] PDF export
- [ ] AI-powered explanation layer

## Disclaimer

For educational and research purposes only. Not a substitute for professional genetic counseling.
