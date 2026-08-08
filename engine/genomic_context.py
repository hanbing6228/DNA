"""Non-clinical genomic context services.

These services deliberately keep ancestry and research traits outside the
clinical reasoning engine.  They surface data provenance and uncertainty
instead of turning population-level associations into diagnoses.
"""
from collections import defaultdict
from math import log
from typing import Dict, Iterable, List

from database.db import GenomicContextRepository


def _alternate_dosage(genotype: str):
    alleles = (genotype or "").split(":", 1)[0].replace("|", "/").split("/")
    if len(alleles) != 2 or any(allele not in {"0", "1"} for allele in alleles):
        return None
    return alleles.count("1")


class GeneFunctionService:
    @staticmethod
    def get_summary(gene_symbol: str) -> List[Dict]:
        return GenomicContextRepository.get_gene_functions(gene_symbol)


class AncestryService:
    """Estimate reference-population similarity from imported marker panels.

    This is a likelihood score, not a statement of identity, ethnicity, or
    nationality. It must have broad marker coverage before being displayed as
    more than exploratory context.
    """

    @staticmethod
    def analyze(variants: Iterable[Dict]) -> Dict:
        marker_index = defaultdict(list)
        for marker in GenomicContextRepository.get_ancestry_markers():
            key = (
                str(marker["chromosome"]).removeprefix("chr"),
                marker["position"],
                marker["reference"],
                marker["alternate"],
            )
            marker_index[key].append(marker)

        log_likelihoods = defaultdict(float)
        matched_loci = set()
        for variant in variants:
            dosage = _alternate_dosage(variant.get("genotype"))
            if dosage is None:
                continue
            key = (
                str(variant.get("chrom", "")).removeprefix("chr"),
                variant.get("pos"),
                variant.get("ref"),
                variant.get("alt"),
            )
            for marker in marker_index.get(key, []):
                frequency = marker["alternate_allele_frequency"]
                probability = (
                    (1 - frequency) ** 2 if dosage == 0
                    else 2 * frequency * (1 - frequency) if dosage == 1
                    else frequency ** 2
                )
                log_likelihoods[marker["population_code"]] += log(max(probability, 1e-12))
                matched_loci.add(key)

        if not log_likelihoods:
            return {
                "status": "not_available",
                "matched_loci": 0,
                "results": [],
                "disclaimer": "No imported ancestry marker panel matched this VCF.",
            }

        highest = max(log_likelihoods.values())
        weights = {
            population: pow(2.718281828, score - highest)
            for population, score in log_likelihoods.items()
        }
        total_weight = sum(weights.values())
        results = [
            {
                "reference_population": population,
                "relative_similarity": round(weight / total_weight, 4),
                "log_likelihood": round(log_likelihoods[population], 3),
            }
            for population, weight in sorted(weights.items(), key=lambda item: item[1], reverse=True)
        ]
        return {
            "status": "exploratory" if len(matched_loci) < 1000 else "reference_panel_estimate",
            "matched_loci": len(matched_loci),
            "results": results,
            "disclaimer": (
                "This is similarity to the imported reference panel, not a medical result "
                "or a determination of ethnicity, identity, or nationality."
            ),
        }
