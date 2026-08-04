import UploadBox from "@/components/UploadBox";

export default function Home() {
  return (
    <main style={{ padding: "2rem", maxWidth: 800, margin: "0 auto" }}>
      <h1>DNA Genome Analyzer</h1>
      <p>Upload your genome file (VCF or VCF.GZ)</p>
      <UploadBox />
    </main>
  );
}
