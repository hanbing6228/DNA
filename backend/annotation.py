def classify_variant(info: str) -> str:
    if "HIGH" in info:
        return "HIGH"
    if "MODERATE" in info:
        return "MODERATE"
    return "LOW"
