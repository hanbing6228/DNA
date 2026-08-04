import requests


def search_clinvar(chrom: str, pos: str, ref: str, alt: str):
    # TODO: replace with local database or bcftools query
    return {
        "clinical_significance": None,
        "source": "ClinVar",
    }
