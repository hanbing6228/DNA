import gzip


def parse_vcf(content: bytes):
    # Try gzip first
    try:
        data = gzip.decompress(content)
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        text = content.decode("utf-8", errors="ignore")

    lines = text.splitlines()
    variants = []

    for line in lines:
        if line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) < 8:
            continue
        chrom = fields[0]
        pos = fields[1]
        ref = fields[3]
        alt = fields[4]
        info = fields[7]
        variants.append({
            "chrom": chrom,
            "pos": pos,
            "ref": ref,
            "alt": alt,
            "info": info,
        })

    return {
        "total_variants": len(variants),
        "variants": variants[:100],
    }
