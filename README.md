# Off-Invoice Rebates

ERPNext V15 app to manage **sconti fuori fattura** (off-invoice rebates) on the sales side: contractual rebates that are NOT applied to the invoice — *premi a target*, *ristorni a fatturato*, *contributi forfettari*, *premi di fine anno*.

---

## 🇬🇧 English

### Features

- **Rebate Agreements** with customer, period, currency, and configurable settlement mode + accounting policy.
- **Four combinable calculators**:
  - **Tiered turnover** — % varies by turnover thresholds.
  - **Volume** — €/unit on quantities sold, filterable by Item Group / Brand.
  - **Target & growth** — bonus on target achievement or YoY growth.
  - **Flat contributions** — fixed periodic amounts (listing fees, promo contributions).
- **Three settlement modes** per Agreement:
  - Automatic **Credit Note** generation (with correct `return_against` linking).
  - **Invoice compensation** — auto-applied on next Sales Invoice for the customer.
  - **Separate Payment Entry** — for cash rebates outside fiscal documents.
- **Three accounting policies** per Agreement:
  - **Full accrual** — periodic GL postings to expense + accrued liability accounts.
  - **On settlement** — GL postings only at settlement time.
  - **Memo-only** — no GL postings, only operational tracking.
- **Italian VAT compliance** — supports both *premio finanziario* (fuori campo IVA, art. 15 DPR 633/72) and *premio in natura* (NC con IVA, art. 26).
- **Scheduled Period Runs** — monthly / quarterly / annual cadences, idempotent.
- **Reports & dashboard** — accrued vs settled, top customers, target attainment.

### Requirements

- ERPNext **v15** (`required_apps = ["erpnext"]`).
- Frappe **v15**.

### Installation

```bash
bench get-app https://github.com/lucsartech/off_invoice_rebates --branch main
bench --site <your-site> install-app off_invoice_rebates
bench --site <your-site> migrate
```

After install, open **Rebate Settings** and configure default accounts, naming series, and causali.

### License

GPLv3 — see `license.txt`.

---

## 🇮🇹 Italiano

### Funzionalità

App ERPNext V15 per la **gestione strutturata degli sconti fuori fattura** lato vendite.

- **Contratti rebate** per cliente, periodo, valuta, con modalità di liquidazione e politica contabile configurabili.
- **Quattro calcolatori combinabili** sul singolo contratto:
  - **Scaglioni di fatturato** — % variabile per soglie.
  - **Volumi** — €/pezzo su quantità vendute, filtrabile per gruppo articoli / marchio.
  - **Target e crescita** — premio al raggiungimento o sulla crescita anno su anno.
  - **Contributi forfettari** — importi periodici fissi (listing, promo, servizi).
- **Tre modalità di liquidazione** per contratto:
  - Generazione automatica **Nota di Credito** (con corretto `return_against`).
  - **Compensazione su fattura** — applicata automaticamente sulla prossima fattura al cliente.
  - **Pagamento separato** — per premi cash fuori campo IVA.
- **Tre politiche contabili** per contratto:
  - **Competenza piena** — scritture periodiche di accantonamento e storno.
  - **Posting solo a liquidazione** — scritture solo all'emissione del documento.
  - **Solo memo** — tracciamento operativo senza scritture in GL.
- **Conformità IVA italiana** — supporta sia *premio finanziario* (fuori campo art. 15 DPR 633/72) sia *premio in natura* (NC con IVA art. 26).
- **Run periodici schedulati** — cadenza mensile/trimestrale/annuale, idempotenti.
- **Report e dashboard** — maturato vs liquidato, top clienti, raggiungimento target.

### Installazione

```bash
bench get-app https://github.com/lucsartech/off_invoice_rebates --branch main
bench --site <tuo-sito> install-app off_invoice_rebates
bench --site <tuo-sito> migrate
```

Dopo l'installazione, apri **Rebate Settings** e configura conti, naming series e causali di default.

### Licenza

GPLv3 — vedi `license.txt`.

---

## Developer notes

Repository structure, sub-agent organization, fiscal rules, and roadmap are documented in `CLAUDE.md` and `docs/`.

**Publisher**: Lucsartech Srl — gianluca.simonini@lucsartech.it
