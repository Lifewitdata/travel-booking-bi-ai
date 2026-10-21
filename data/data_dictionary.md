# Data dictionary - fact_bookings_clean.csv

Source columns keep their original names (hotel, is_canceled, lead_time,
arrival_date_year/month/day, stays_in_weekend_nights, stays_in_week_nights,
adults, children, babies, meal, country, market_segment,
distribution_channel, is_repeated_guest, previous_cancellations,
previous_bookings_not_canceled, reserved_room_type, assigned_room_type,
booking_changes, deposit_type, agent, company, days_in_waiting_list,
customer_type, adr, required_car_parking_spaces,
total_of_special_requests, reservation_status, reservation_status_date).

Derived columns:
- arrival_date: full arrival date built from year/month/day
- booking_date: arrival_date - lead_time days
- total_nights: weekend + week nights
- guests: adults + children + babies
- is_realized: 1 only when reservation_status = 'Check-Out'
- is_noshow: 1 when reservation_status = 'No-Show'
- booked_revenue_eur: adr * total_nights (all rows)
- realized_revenue_eur: booked revenue when is_realized = 1, else 0
- commission_rate, acquisition_cost_per_booking_eur, is_synthetic:
  from data/reference/channel_costs.csv (SYNTHETIC reference layer)
- commission_cost_eur, acquisition_cost_eur, channel_cost_eur
- gross_margin_eur: realized revenue - channel cost
- arrival_week (Monday start), arrival_month
- quarantine_reason: only on quarantined_rows.csv
