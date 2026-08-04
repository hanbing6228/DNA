interface Props {
  level: "low" | "moderate" | "high";
}

const colors: Record<string, string> = {
  low: "#090",
  moderate: "#880",
  high: "#c00",
};

const labels: Record<string, string> = {
  low: "Low",
  moderate: "Moderate",
  high: "High",
};

export default function RiskBadge({ level }: Props) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.25rem 0.75rem",
        borderRadius: 999,
        background: colors[level] + "15",
        color: colors[level],
        fontWeight: 600,
        fontSize: "0.9rem",
      }}
    >
      {labels[level]}
    </span>
  );
}
