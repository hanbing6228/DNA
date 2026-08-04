import GenomeSummary from "@/components/GenomeSummary";

export default function Dashboard() {
  return (
    <div style={{ padding: "2rem", maxWidth: 800, margin: "0 auto" }}>
      <h1>Genome Dashboard</h1>
      <GenomeSummary
        totalVariants={93525}
        pathogenic={3}
        likelyPathogenic={12}
        benign={45000}
        vus={120}
      />
    </div>
  );
}
