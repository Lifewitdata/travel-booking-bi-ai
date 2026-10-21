# Experiment memo - flexible free-cancellation rate (SIMULATED)

Design: 20,000 booking-flow users, 50/50, seed 42. Simulated data,
built to demonstrate a correct readout - it is not real guest data.
Primary: booking conversion. Guardrails: cancellation rate among
bookers, revenue per user. Rules were set before looking at results:
ship only if conversion improves significantly and neither guardrail
degrades significantly.

Results:
- SRM: 9,938 control / 10,062 treatment, chi-square p = 0.381 - clean
- Conversion: 11.99% -> 13.16%, lift +9.7%, p = 0.013 - significant
- Cancellation among bookers: 37.6% -> 40.2%, p = 0.182 - not significant
- Revenue per user: EUR 25.15 -> EUR 26.45, p = 0.307 - not significant

Power note: detecting a 37% -> 41% cancellation change needs about
2,333 bookers per arm, i.e. about 19,400 users per arm at 12%
conversion. The test ran with about 10,000 per arm, so the guardrail
readout is underpowered - 'not significant' here means 'unresolved',
not 'no effect'.

Decision: SHIP WITH MONITORING. Weekly cancellation monitoring for
4 weeks with a pre-set stop rule; re-run the guardrail readout at
full power before the rate becomes permanent.
