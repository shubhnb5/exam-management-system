// The Combine Mentor seal: an ink disc with a marigold rim and a perforated
// inner ring (like an examination stamp / admit-card perforation).
export default function BrandSeal({ size = 40, className = "" }) {
  return (
    <svg
      className={`brand-seal ${className}`}
      width={size}
      height={size}
      viewBox="0 0 48 48"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="24" cy="24" r="23" fill="#12163A" />
      <circle cx="24" cy="24" r="21" fill="none" stroke="#F2A93B" strokeWidth="1.6" />
      <circle cx="24" cy="24" r="17.2" fill="none" stroke="#F2A93B" strokeWidth="1.2" strokeDasharray="1.2 2.6" opacity="0.85" />
      <text
        x="24"
        y="29.2"
        textAnchor="middle"
        fontFamily="'Fraunces Variable', Georgia, serif"
        fontWeight="700"
        fontSize="15"
        letterSpacing="0.5"
        fill="#FFF8EA"
      >
        CM
      </text>
    </svg>
  );
}
