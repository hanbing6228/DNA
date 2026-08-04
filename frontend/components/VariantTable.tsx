interface Variant {
  gene: string;
  hgvs: string;
  clnsig: string;
}

interface Props {
  variants: Variant[];
}

export default function VariantTable({ variants }: Props) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "1rem" }}>
      <thead>
        <tr style={{ background: "#f5f5f5", textAlign: "left" }}>
          <th style={{ padding: "0.6rem", borderBottom: "2px solid #ddd" }}>Gene</th>
          <th style={{ padding: "0.6rem", borderBottom: "2px solid #ddd" }}>Variant</th>
          <th style={{ padding: "0.6rem", borderBottom: "2px solid #ddd" }}>Clinical</th>
        </tr>
      </thead>
      <tbody>
        {variants.map((v, i) => (
          <tr key={i} style={{ borderBottom: "1px solid #eee" }}>
            <td style={{ padding: "0.6rem" }}>{v.gene}</td>
            <td style={{ padding: "0.6rem", fontFamily: "monospace" }}>{v.hgvs}</td>
            <td style={{ padding: "0.6rem" }}>{v.clnsig}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
