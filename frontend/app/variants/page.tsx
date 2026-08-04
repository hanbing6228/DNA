import VariantTable from "@/components/VariantTable";

const dummyVariants = [
  { gene: "BRCA1", hgvs: "c.68_69delAG", clnsig: "Pathogenic" },
  { gene: "BRCA2", hgvs: "c.9097_9098del", clnsig: "Likely pathogenic" },
  { gene: "CFTR", hgvs: "c.1521_1523delCTT", clnsig: "Pathogenic" },
  { gene: "APOE", hgvs: "c.388T>C", clnsig: "Risk factor" },
];

export default function VariantsPage() {
  return (
    <div style={{ padding: "2rem", maxWidth: 1000, margin: "0 auto" }}>
      <h1>Variant Report</h1>
      <VariantTable variants={dummyVariants} />
    </div>
  );
}
