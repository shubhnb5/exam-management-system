import logo from "../assets/cm-logo.jpg";

// The official Combine Mentor logo. The artwork has a white background, so it
// sits on a white rounded tile that reads well on the dark hero panel.
export default function BrandLogo({ className = "" }) {
  return (
    <span className={`brand-logo ${className}`}>
      <img src={logo} alt="Combine Mentor Official logo" width="320" height="237" decoding="async" />
    </span>
  );
}
