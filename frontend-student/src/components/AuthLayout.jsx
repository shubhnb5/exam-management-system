import { APP_VERSION } from "../version";
import BrandSeal from "./BrandSeal";

export default function AuthLayout({ title, subtitle, children, footer, beforeForm }) {
  return (
    <div className="auth-page">
      <aside className="auth-hero guilloche">
        <div className="brand">
          <BrandSeal size={44} />
          <div>
            <div className="brand-name">Combine Mentor</div>
            <div className="brand-sub">Student Portal</div>
          </div>
        </div>
        <h2 className="auth-hero-title">
          Your admit card, <em>one tap away.</em>
        </h2>
        <ol className="auth-steps">
          <li>
            <span className="step-no">01</span>
            <strong>Register with your mobile number</strong>
            <span>Use the same number your institute has on record.</span>
          </li>
          <li>
            <span className="step-no">02</span>
            <strong>Log in any time</strong>
            <span>Your mobile number and password are all you need.</span>
          </li>
          <li>
            <span className="step-no">03</span>
            <strong>Download &amp; print</strong>
            <span>Bring the printed admit card to your exam centre.</span>
          </li>
        </ol>
      </aside>

      <div className="auth-main">
        <main className="auth-card">
          <h1 className="auth-title">{title}</h1>
          {subtitle && <p className="auth-subtitle">{subtitle}</p>}
          {beforeForm}
          {children}
        </main>

        {footer && <div className="auth-footer">{footer}</div>}
        <div className="app-version">{APP_VERSION}</div>
      </div>
    </div>
  );
}
