# NYC 311 Service Requests (CY 2023) — Data Quality Profiling Report

**Total Records Analyzed**: 25,000

## 1. Column Completeness & Missing Value Rates

| Column Name | Missing Count | Missing % |
|---|---|---|
| `unique_key` | 0 | 0.00% |
| `created_date` | 0 | 0.00% |
| `closed_date` | 286 | 1.14% |
| `agency` | 0 | 0.00% |
| `agency_name` | 0 | 0.00% |
| `complaint_type` | 0 | 0.00% |
| `descriptor` | 181 | 0.72% |
| `location_type` | 2,276 | 9.10% |
| `incident_zip` | 238 | 0.95% |
| `city` | 1,035 | 4.14% |
| `borough` | 0 | 0.00% |
| `latitude` | 271 | 1.08% |
| `longitude` | 271 | 1.08% |
| `status` | 0 | 0.00% |
| `resolution_description` | 181 | 0.72% |
| `open_data_channel_type` | 0 | 0.00% |

## 2. Pre-Existing Data Quality Problems Found

- **Closed Date Earlier than Created Date**: 3 records (0.012%)
- **Missing Geolocation Coordinates**: 271 records
- **Coordinates Outside NYC Bounding Box**: 0 records
- **Closed Status Contradicting Ongoing Text**: 42 records
- **Closed Requests with Empty Resolution**: 128 records
- **Potential Duplicates (Same Event & Location)**: 561 records
- **Pre-existing PII (Phone/Email) in Free Text**: 757 records

## 3. Categorical Distributions

### Top Complaint Types
- **Illegal Parking**: 4,337
- **Noise - Residential**: 3,108
- **HEAT/HOT WATER**: 2,641
- **Blocked Driveway**: 1,784
- **Noise - Commercial**: 834
- **Noise - Street/Sidewalk**: 701
- **UNSANITARY CONDITION**: 701
- **Abandoned Vehicle**: 644
- **PLUMBING**: 424
- **Noise - Helicopter**: 395

### Top Agencies
- **NYPD**: 12,803
- **HPD**: 5,441
- **DSNY**: 2,125
- **DOT**: 985
- **DEP**: 962
- **DOB**: 693
- **DOHMH**: 602
- **DPR**: 417
- **EDC**: 395
- **DHS**: 237