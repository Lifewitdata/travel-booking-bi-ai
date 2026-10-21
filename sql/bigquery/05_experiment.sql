-- A/B readout for the simulated free-cancellation experiment.
-- Table experiment_users is SIMULATED (seed 42) - see src/ab_test.py.
-- booked / cancelled upload as BOOL, so cast before averaging.
SELECT
  variant,
  COUNT(*) AS users,
  AVG(CAST(booked AS INT64)) AS conversion_rate,
  AVG(IF(booked, CAST(cancelled AS INT64), NULL)) AS cancel_rate_among_bookers,
  AVG(revenue_per_user_eur) AS revenue_per_user_eur
FROM travel_bi.experiment_users
GROUP BY variant;
-- SRM and significance are computed in Notebook 03 (chi-square + z-test);
-- SQL reports the raw rates so the two layers can be cross-checked.
