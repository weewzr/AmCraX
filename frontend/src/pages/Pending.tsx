export default function Pending({ title, description }: { title: string; description: string }) {
  return (
    <section className="page">
      <h1>{title}</h1>
      <div className="card pending">
        <strong>Module pending.</strong> {description} This section is not implemented yet; no results are shown rather than placeholder charts.
      </div>
    </section>
  )
}
