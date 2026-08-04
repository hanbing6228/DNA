import re

class VariantNormalizer:
    """Normalize VCF variants for consistent matching."""

    @staticmethod
    def normalize_chrom(chrom):
        """Remove 'chr' prefix, handle MT/chrM."""
        chrom = str(chrom).strip().upper()
        if chrom.startswith('CHR'):
            chrom = chrom[3:]
        if chrom in ('M', 'MT', 'CHRM'):
            chrom = 'MT'
        return chrom

    @staticmethod
    def normalize_alleles(ref, alt):
        """Trim common prefix/suffix for minimal representation."""
        ref = str(ref).upper()
        alt = str(alt).upper()

        # Left-align trim
        while len(ref) > 0 and len(alt) > 0 and ref[0] == alt[0]:
            ref = ref[1:] if len(ref) > 1 else ''
            alt = alt[1:] if len(alt) > 1 else ''

        # Right-align trim
        while len(ref) > 0 and len(alt) > 0 and ref[-1] == alt[-1]:
            ref = ref[:-1] if len(ref) > 1 else ''
            alt = alt[:-1] if len(alt) > 1 else ''

        return ref or '-', alt or '-'

    @staticmethod
    def create_key(chrom, pos, ref, alt):
        """Create a normalized lookup key."""
        chrom = VariantNormalizer.normalize_chrom(chrom)
        ref, alt = VariantNormalizer.normalize_alleles(ref, alt)
        return f"{chrom}:{pos}:{ref}:{alt}"
