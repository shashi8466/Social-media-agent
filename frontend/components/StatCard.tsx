interface StatCardProps {
  label: string;
  value: number | string;
  icon: string;
  gradient: string;
  description: string;
}

export default function StatCard({ label, value, icon, gradient, description }: StatCardProps) {
  return (
    <div className="card" style={{ position: 'relative', overflow: 'hidden' }}>
      <div style={{
        position: 'absolute', top: '-20px', right: '-20px', width: '80px', height: '80px',
        borderRadius: '50%', background: gradient, opacity: 0.08, filter: 'blur(20px)'
      }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ color: 'var(--text-muted)', fontSize: '13px', fontWeight: 500, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            {label}
          </div>
          <div style={{ fontSize: '36px', fontWeight: 800, fontFamily: 'Space Grotesk', lineHeight: 1, background: gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
            {value}
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '6px' }}>{description}</div>
        </div>
        <div style={{
          width: '48px', height: '48px', borderRadius: '12px',
          background: gradient, display: 'flex', alignItems: 'center',
          justifyContent: 'center', fontSize: '22px', opacity: 0.9, flexShrink: 0
        }}>{icon}</div>
      </div>
    </div>
  );
}
