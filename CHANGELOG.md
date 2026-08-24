# CHANGELOG


## [unreleased]

### Fixed
- CI
  - Test workflow ran on the retired `ubuntu-20.04` image and never got a runner, so no
    test has actually executed since mid 2025. Now runs on `ubuntu-24.04`
  - `Schedule.autofill_slots` test called the method without its `interest_type` argument

### Changed
- CI
  - Consolidated the three workflow files into a single `test.yml` (no more duplicate runs
    per branch), bumped the deprecated `actions/checkout@v2`/`setup-python@v2`, added
    dependency caching, a concurrency group, a job timeout and a missing-migration check
  - Removed Travis configuration; GitHub Actions is the only CI

## [2026.3.1] - 2026-03-03

### Changed
- Frontend
  - Migrated UI library (Mantine) from v6 to v8
  - Fixed active navbar item being invisible after migration

## [2024.9.21] - 2024-09-21

### Added
- Organization: internal group position highlight filter on archive status

## [2024.8.1] - 2024-08-13
### Added
- Schedules
  - Allergy resolver counting allergies per day based on shifts

## [2024.03.8] - 2024-03-08
### Added
- Organization
  - New mutation for memberships

### Fixed
- Users
  - Incorrect user position membership start date (used date_ended)
- Economy
  - Add product_id to stock price history resolver returndata


## [2023.11.1] - 2023-11-09
### Added
- Stock market mode
  - Feature flag based mode that triggers a new purchase mode emulating the fluctuations of a stock market
    - X-APP purchases made through the REST API will calculate a price based on the item purchase price and popularity
    - Ghost product purchases to track non-digital pucrhases made
    - Stock market crash model to manually crash the market through am utation
    - Queries to show stock market item and its price change
    - A whole lot of tests

### Fixed
- Economy
  - Broken statistics query

### Removed
- Economy
  - Redundant is_default field annotation in product resolver 

## [2023.9.1] - 2023-09-12

### Changed
- Economy
  - Automatically close stale soci order sessions when attempting to create a new one.
  - Add resolvers for sales statistics on products

## [2023.8.2] - 2023-08-21

### Added

- Organization
  - Admission membership type resolver on InternalGroupPositionNode

## [2023.8.1] - 2023-08-03

### Added

- Economy
  - Debt collection utility. Retrieve all users with a balance lower than debt collection threshold
  and option to send collections email. Email includes frontend url with an auth token which should
  immediately load the deposit form in /torpedo
- Admissions
  - Applicant recommendation model
  - Ordering key to internal group applicant data query
  - Default interview notes

### Changed
- Dependencies
  - Upgrade Django to 4.2
  - Upgrade graphene-django to v3
  - Upgrade graphene-django-cud
  - Change drf-yasg2 to drf-yasg which is maintaned again


### Fixed
- Admissions
  - Change priorities when admission is in session
  - Incorrect CreateAdmission mutation permission
- Common
  - Breaking use of Exception (IllegalOperation)

## [2023.5.1] - 2023-05-16

### Changed

- Economy
  - Refactor deposit fee to be added to charge instead of
  subtracted

## [2023.4.1] - 2023-04-18

### Added
- Economy
  - `minimum_remaining_balance` field to SociSession
  - Change PlaceProductOrderMutation to check for `minimum_remaining_balance`
    against SociSession
- Schedules
  - autofill method based on shift interest
  - WIP shift interest and roster models/methods

### Fixed
- Economy
    - Incorrect overcharge permission check in PlaceProductOrderMutation

## [2023.3.2] - 2023-03-10

### Added
- Common
  - reply_to field in send mail util
- Economy
  - overcharge argument to add product order mutation

### Changed
- Economy
  - Return all deposits in  all_deposits resolver instead of only bank transfer type
  - Add Invalidate mutation deposit method check
    - Cannot invalidate stripe deposits
  - Bar tab invoice
    - Conditional away orders rendering
    - Hardcode reference email
    - Add summary per item/customer to invoice

### Fixed
- Economy
  - Missing permission check for bank account mutation
  - Exclude balance from bank account mutation
  - QR code being written to disc
- Common
  - Missing cc kwarg in send mail util

## [2023.3.1] - 2023-03-04

### Added
- Common: Flags to enable/disable features

### Changed
- Economy: Stripe webhook add refund event
- Economy: Create deposit mutation.
    * Handle stripe and bank transfer payments
	
## [v2023.2.3] - 2023-02-14

### Changed

- Economy: raise min value deposit to Stripe minium (3 NOK)

### Fixed

- Quotes: incorrect approve/invalidate permissions
- Economy: util function docstring typos

## [v2023.2.2] - 2023-02-10

### Added

- Economy: Stripe intergration
	* Dependencies
	* Payment intent creation
	* Customer creation
	* Payment verification webhook

## [v2023.2.1] - 2023-02-10

### Fixed

- Schedules: Incorrect depsits resolver permission

## [v2023.1.7] - 2023-01-29
- Common: Dashboard data resolver for newbies
- Users: Resolver for new users

## [v2023.1.6] - 2023-01-27

### Fixed
- Admissions: Interview statistics N+1 query issue
- Schedules: Missing 'Kontoret' option for location
- Schedules: Missing 'Ryddevakt' option for role
- Users: User search performance

### Changed
- UpdateDocumentMutation -> PatchDocumentMutation

## [v2023.1.5] - 2023-01-??

Things happend. Not sure what.

## [v2023.1.4] - 2023-01-15

### Added
- Strip email on password reset for leading and trailing whitespace
- Strip email on applicant resend token for leading and trailing whitespace
- Activity logging to applicant mutation and queries

### Fixed
- Approve deposit duplicate approval bug

## [v2023.1.3] - 2023-01-14
### Added
- Resolver for interview overview
- Internal group user highlight model
- Admin site search fields for some models

### Changed
- Applicant email is direct instead of bcc now

## [v2023.1.2] - 2023-01-13
### Added
- API charge bank account logging
- Owes money resolver on UserNode
- CORS headers for sentry frontend tracing
- User and Quote field escaping
- Close stale order session management command and script
- Add versioning to settings
- Added a CHANGELOG.md file to track changes to the project.
- Add Shift model save method override if `datetime_start` is greater than `datetime_end`

### Changed
- Wrap purchases in transactions

### Fixed
- Apply schedule template bug

## [v2023.1.1] - 2023-01-07

First release.

### Added
- Quote module
- Schedule module
- Bar tab module
- Admission module
- Economy module
- Login module
- Summary module
- User module
- Handbook module
- Economy API
- Organization module
