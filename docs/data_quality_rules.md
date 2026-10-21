# Data quality rules and catches

Reconciliation: raw 119,390 = clean 119,209 + quarantined 181. Exact.

Quarantine (only these leave the clean fact):
- guests = 0 (180 rows): a booking with no guests cannot be a stay
- adr > 1,000 (1 row, adr = 5,400): single outlier, would poison averages

Kept and flagged (dropping these would be the error):
- 31,994 byte-identical rows: no booking ID exists in the source, so
  identical rows are separate bookings. Never dedupe this dataset.
- 645 zero-night rows and 1,810 zero-ADR rows in the clean fact:
  complimentary / day-use bookings, revenue honestly 0.
- children is null on 4 rows: filled with 0 after checking the pattern.
- country is the string 'NULL' / missing on 488 rows: set to 'Unknown'.

Source quirks carried, not interpreted:
- All 1,207 No-Show rows have is_canceled = 1 in the source.
- 'Non Refund' deposit rows are 99.4% canceled in the source. Reported
  wherever deposit appears, with a warning. No policy claim is made
  from it; it needs Finance verification (non-refundable cancellations
  normally still pay).
- Missing values arrive as the literal string 'NULL'; the loader must
  use na_values=['NULL'] or country/agent/company are misread.
