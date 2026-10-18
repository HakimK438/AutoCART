import React from 'react';
import { Printer } from 'lucide-react';
import { LogoMark } from '../../storefront/Brand';

const row = (label, value) => (value ? <tr key={label}><th scope="row">{label}</th><td>{value}</td></tr> : null);

/** The seller application as a one-page form with the AutoCart logo. "Print or save as PDF" uses the browser's print dialog. */
export default function ApplicationPrintForm({ app }) {
  if (!app) return null;
  const id = app.identity || {};
  const store = app.store || {};
  const when = new Date(app.submittedAt || app.updatedAt || Date.now()).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
  const address = [store.address || app.address, store.city || app.city, store.state || app.addressState, store.pincode || app.pincode].filter(Boolean).join(', ');
  const checks = app.comparison?.checks || [];
  return (
    <section className="ac-printwrap">
      <div className="ac-row-between ac-noprint" style={{ marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>Your application form</h2>
        <button type="button" className="ac-btn ac-btn-blue ac-btn-small" onClick={() => window.print()}><Printer size={16} /> Print or save as PDF</button>
      </div>
      <article className="ac-printform" aria-label="Seller application form">
        <header>
          <div className="ac-pf-brand"><LogoMark size={44} /><div><b>AutoCart</b><small>Local-store marketplace</small></div></div>
          <div className="ac-pf-ref"><b>Seller application</b><small>Ref {app.id}</small><small>{when}</small></div>
        </header>

        <h3>1. Applicant</h3>
        <table><tbody>
          {row('Full name', app.applicantName)}{row('Phone', app.phone)}{row('Email', app.email)}
          {row('Aadhaar (masked)', id.aadhaarMasked || (app.aadhaarLast4 && `XXXX-XXXX-${app.aadhaarLast4}`))}
          {row('PAN', app.pan || id.pan)}{row('Date of birth', id.dob)}
        </tbody></table>

        <h3>2. Store</h3>
        <table><tbody>
          {row('Business name', app.companyName)}{row('Store name', app.storeName || app.companyName)}{row('Business type', app.businessType)}
          {row('Address', address)}
          {row('Map location', store.latitude != null && store.longitude != null ? `${Number(store.latitude).toFixed(5)}, ${Number(store.longitude).toFixed(5)}` : '')}
        </tbody></table>

        <h3>3. Bank account</h3>
        <table><tbody>
          {row('Account holder', id.accountHolder)}{row('Bank', [id.bankName, id.branch].filter(Boolean).join(', '))}
          {row('IFSC', id.ifsc)}{row('Account number', id.accountLast4 && `ending ${id.accountLast4}`)}
        </tbody></table>

        {checks.length > 0 && (<>
          <h3>4. Automatic checks</h3>
          <table><tbody>{checks.map((c) => row(c.label, c.status === 'match' ? 'Matches the document' : c.status === 'mismatch' ? 'Does not match: needs review' : 'Could not be read'))}</tbody></table>
        </>)}

        <p className="ac-pf-note">I confirm these details are correct. My documents were read automatically and will be reviewed by AutoCart staff. Only the last 4 digits of my Aadhaar and bank account are kept.</p>
        <footer><div><span /><small>Applicant signature</small></div><div><span /><small>AutoCart reviewer</small></div></footer>
      </article>
    </section>
  );
}
