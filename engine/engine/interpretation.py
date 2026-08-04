class VariantInterpreter:
    """Generate human-readable interpretations."""

    DISEASE_DESCRIPTIONS = {
        'Hereditary pancreatitis': 'A genetic condition causing recurrent inflammation of the pancreas, often starting in childhood or adolescence.',
        'Hereditary breast-ovarian cancer syndrome': 'Increased lifetime risk of breast and ovarian cancers due to DNA repair gene variants.',
        'Cystic fibrosis': 'Affects the lungs and digestive system by producing thick, sticky mucus.',
        'Late-onset Alzheimer\'s disease': 'The most common form of dementia, with genetic factors influencing risk.',
        'Factor V Leiden thrombophilia': 'Increased tendency to form abnormal blood clots, especially in deep veins.',
        'Hereditary hemochromatosis': 'Excess iron absorption leading to organ damage if untreated.',
        'Hyperhomocysteinemia': 'Elevated homocysteine levels, associated with cardiovascular risk.',
    }

    RECOMMENDATIONS = {
        'pathogenic': [
            'Discuss with a genetic counselor or specialist',
            'Consider family screening if indicated',
            'Follow condition-specific surveillance guidelines',
        ],
        'likely_pathogenic': [
            'Discuss with healthcare provider',
            'Consider confirmatory testing if clinically indicated',
            'Monitor for related symptoms',
        ],
        'risk_factor': [
            'Discuss with healthcare provider',
            'Consider lifestyle modifications',
            'Monitor relevant biomarkers',
        ],
        'drug_response': [
            'Share with prescribing physician',
            'May affect medication dosing or selection',
        ],
    }

    @classmethod
    def interpret(cls, variant_data):
        """Generate full interpretation for a variant."""
        gene = variant_data.get('gene_name', 'Unknown')
        hgvs_p = variant_data.get('hgvs_p', '')
        disease = variant_data.get('disease', '')
        significance = variant_data.get('clinvar_significance', '')
        impact = variant_data.get('impact', '')

        # Build interpretation
        interpretation = {
            'gene': gene,
            'variant': hgvs_p or variant_data.get('hgvs_c', ''),
            'significance': significance,
            'impact': impact,
            'disease': disease,
            'disease_description': cls.DISEASE_DESCRIPTIONS.get(disease, ''),
            'recommendations': cls.RECOMMENDATIONS.get(significance, [
                'Consult with healthcare provider for interpretation'
            ]),
            'summary': cls._generate_summary(variant_data),
        }

        return interpretation

    @classmethod
    def _generate_summary(cls, data):
        """Generate a one-sentence summary."""
        gene = data.get('gene_name', '')
        sig = data.get('clinvar_significance', '')
        disease = data.get('disease', '')
        impact = data.get('impact', '')

        if sig in ('pathogenic', 'likely_pathogenic'):
            return f"A {sig.replace('_', ' ')} variant in {gene} associated with {disease}." if disease else f"A {sig.replace('_', ' ')} variant in {gene}."
        elif sig == 'risk_factor':
            return f"A risk factor variant in {gene} that may influence {disease}." if disease else f"A risk factor variant in {gene}."
        elif sig == 'drug_response':
            return f"A pharmacogenomic variant in {gene} that may affect drug response."
        elif impact == 'HIGH':
            return f"A high-impact variant in {gene} with uncertain clinical significance."
        else:
            return f"A variant in {gene} with no known clinical significance."
