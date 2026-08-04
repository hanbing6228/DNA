import RiskBadge from "./RiskBadge";

interface Props {
  totalVariants: number;
  pathogenic: number;
  likelyPathogenic: number;
  benign: number;
  vus: number;
}

export default function GenomeSummary({
  totalVariants,
  pathogenic,
  likelyPathogenic,
  benign,
  vus,
}: Props) {
  return (
    <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
      <div style={{ padding: "1rem", border: "1px solid #ddd", borderRadius: 8 }}>
        <div style={{ fontSize: "0.85rem", color: "#666" }}>Total Variants</div>
        <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{totalVariants.toLocaleString()}</div>
      </div>
      <div style={{ padding: "1rem", border: "1px solid #ddd", borderRadius: 8 }}>
        <div style={{ fontSize: "0.85rem", color: "#666" }}>Pathogenic</div>
        <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#c00" }}>{pathogenic}</div>
      </div>
      <div style={{ padding: "1rem", border: "1px solid #ddd", borderRadius: 8 }}>
        <div style={{ fontSize: "0.85rem", color: "#666" }}>Likely Pathogenic</div>
        <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#e66" }}>{likelyPathogenic}</div>
      </div>
      <div style={{ padding: "1rem", border: "1px solid #ddd", borderRadius: 8 }}>
        <div style={{ fontSize: "0.85rem", color: "#666" }}>Benign</div>
        <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#090" }}>{benign.toLocaleString()}</div>
      </div>
      <div style={{ padding: "1rem", border: "1px solid #ddd", borderRadius: 8 }}>
        <div style={{ fontSize: "0.85rem", color: "#666" }}>VUS</div>
        <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#880" }}>{vus}</div>
      </div>
      <div style={{ padding: "1rem", border: "1px solid #ddd", borderRadius: 8 }}>
        <div style={{ fontSize: "0.85rem", color: "#666" }}>Overall Risk</div>
        <RiskBadge level="moderate" />
      </div>
    </div>
  );
}
