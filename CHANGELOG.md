# CHANGELOG


## [unreleased]

## [2026.10.3]

### Added
- Schedules: planning of shifts (beta)
  - `Schedule.internal_group` (set in the Django admin) limits who manages a schedule to the
    active functionaries of the group, and to superusers. A schedule without a group is managed
    by anyone with the permission, as before
  - Roster: `ScheduleNode.roster`, `rosterGroupings` and `rosterSyncPreview`, and mutations for
    the rules, the rows and the sync from the memberships (`schedules.change_schedule`)
  - `PlanningPeriod`: `createPlanningPeriod`, `updatePlanningPeriod`, `deletePlanningPeriod`
    (not when published) and `myOpenPlanningPeriods`. The status comes from `deadline` and
    `published_at`
  - `setShiftInterest`: one answer per user and shift, with a note, for users on the roster of
    an open period. `PlanningPeriodNode.myDefaultAvailability` gives the default of the user
  - Weekly unavailability (`UserUnavailability`) that pre-fills "cannot work" answers, with
    `unavailabilityPreview` and `blockedShiftCount`
  - Drafts of slot changes: `draftSlot`, `discardDraft` and `lockDraft`, `ShiftSlotNode.draft`
    and `ScheduleNode.draftCount`. Members see a change after the lock, and a lock sends one
    email per user with `notify_on_shift`. `publishPlanningPeriod` locks the drafts in the dates
    of the period and sets `published_at`
  - Autofill: `runAutofill` and `revertAutofillRun` make drafts for the empty slots, with a
    reason for each slot it cannot fill. `PlanningPeriodNode.autofillRuns`
  - `sendPlanningPeriodReminder`, `responseStats` and `slotCoverage` (with
    `candidateBreakdown` by membership type) for the managers
  - `templateGenerationPreview`, and `generateShiftsFromTemplate(confirmDelete)`
  - `scheduleAllergiesV2` takes `timeFrom` and `timeTo`, to count only shifts that overlap a
    clock window, for example soup time
- Economy: `SociProduct.Type.VOUCHER` and `isVoucher` on the sales statistics rows, so a voucher
  like bong is not counted as revenue
- Common: `truthOrDrinkEnabled` tells the SPA if the hidden party game is on. It reads the
  `truth_or_drink` feature flag (`TRUTH_OR_DRINK_FEATURE_FLAG`), which is off by default.
  Needs login

### Changed
- Schedules: `setShiftInterest` replaces `createShiftInterest`
- Schedules: `generateShiftsFromTemplate` replaces the shifts of the template only in the weeks
  it makes, and refuses to delete filled slots, answers or drafts without `confirmDelete`
- Schedules: the shift queries need login (`myUpcomingShifts`, `allMyShifts`, `allShifts`,
  `allUsersWorkingToday` and `normalizedShiftsFromRange`)
- Common: `sendFeedback` needs the `feedback` feature flag (`FEEDBACK_FEATURE_FLAG`). It is off
  by default. `dashboardData.showFeedback` tells the dashboard if the flag is on

### Fixed
- Schedules: a query for `ShiftSlotNode.draft.autofillRun` of a manual draft, or for
  `ScheduleRoster.grouping` of a row without a grouping, failed with "matching query does not
  exist". Both fields now give `null`

### Migrations
- Schedules `0010`–`0020` and economy `0007`. `0012` deletes `ScheduleRoster` rows without a
  role (when the schedule has no default role) and duplicate rows. `0015` deletes duplicate
  `ShiftInterest` rows and keeps the newest. Neither can be reversed. Back up the database first

## [2026.10.2]

### Changed
- Admin: faster admin pages, with search and filters
- Quotes: `QuoteNode.sum` is annotated, so it no longer makes one query per quote
- Monitoring: Sentry names the GraphQL transactions by operation and reports resolver errors

## [2026.10.1]

### Added
- Economy
  - Sales statistics grouped by day, week, month or semester, and for all time. Without
    `productIds`, the products sold in the range are used
  - `myPurchasesByPeriod` for the Min økonomi page
- Organization: `setUserMembershipHistory` to correct a user's verv timeline
- Schedules: `scheduleAllergiesV2`, a weekly allergy matrix with the number of people at
  work per day
- Schedules: `plannedUntil`, `upcomingSlots(days)` and `recentLocations(weeks)` on
  `ScheduleNode` for the schedules overview (`schedules.change_schedule`)
- Schedules: `createShiftWithSlots` and `updateShiftDetails` for the new schedule view. They
  take a date and clock times and combine them in `TIME_ZONE`, so the browser time zone
  does not matter; an end at or before the start is the next day
- Common: `sendFeedback`, feedback from the dashboard as an email to `FEEDBACK_EMAIL`
  (default `ksg-it@samfundet.no`). Max 500 characters and 5 per user per hour; plain text
  and HTML; a reference per submission in the subject, so each feedback is its own thread
- Logging: `RequestLogMiddleware` logs one line per request (the Varnish request id,
  GraphQL operation, user id, status, sizes and time) and returns it as `X-Request-ID`.
  `LOG_LEVEL` sets the level; errors and requests slower than `REQUEST_LOG_SLOW_MS`
  (default 2000) are always logged as warnings
- Tests for invoice and food order PDFs, rich text sanitizing, the API docs and the
  charge errors

### Changed
- Dependencies
  - Django 4.2 -> 5.2 LTS. `pytz` replaced by `zoneinfo`
  - scipy and numpy removed: shift autofill uses an in-house bipartite matching
  - WeasyPrint 54 -> 70, bleach 5 -> 6.4 (XSS fixes), pyjwt 2.15,
    djangorestframework-simplejwt 5.5, drf-yasg 1.21.15, graphene-django 3.2,
    graphene-django-cud 0.13, django-filter 25, DRF 3.18, sentry-sdk 2, urllib3 2.8,
    sqlparse 0.6. setuptools is no longer needed
  - Python 3.11 to 3.13
- API: `POST /api/economy/charge` returns 402 for insufficient funds and 424 when no
  Soci session is active (was 400), so the X-App shows a message
- Bar tab: compact invoice rows, and the KSG logo is part of the repo
- Economy: bank account and balance fields only for the owner or
  `economy.view_socibankaccount`; sales statistics need `economy.view_productorder`
- Schedules: the allergy queries need `schedules.change_schedule`
- Schedules: `allSchedules` and `shiftsFromRange` need login
- Settings: `AUTH_JWT_SECRET` comes from the environment. Production and dev refuse to start
  without it, or with less than 32 characters, and the X-App tokens use the same key.
  Everyone is logged out once after the deploy
- Admissions: no per-applicant queries in the applicant lists; `currentApplicants`
  prefetches priorities
- Settings: dev server settings are in `settings_development.py`
- CI
  - Consolidated the three workflow files into a single `test.yml` (no more duplicate runs
    per branch), bumped the deprecated `actions/checkout@v2`/`setup-python@v2`, added
    dependency caching, a concurrency group, a job timeout and a missing-migration check
  - Removed Travis configuration; GitHub Actions is the only CI
  - Tests run on Python 3.11 and 3.13

### Fixed
- Time zones: day boundaries for shifts and shift generation had a +01:22 offset; the end
  of summer time is handled; the interview booking soft wall compared local time as UTC
- Bar tab: invoice reply-to address (`ksg-soci-okonomi@samfundet.no`), and the invoice
  logo, which returned 404
- Rich text: the `u` tag is allowed, so underline from the editor is kept
- Schedules: shift slots keep their order after a slot is filled; `myUpcomingShifts` and
  `allMyShifts` return each shift once
- Economy: removed a second `allSociSessions` resolver that deleted all sessions
- Admissions: uploaded images are validated, and old applicant images are cleaned up;
  `generate_active_admission` makes data that matches the current models
- CI
  - Test workflow ran on the retired `ubuntu-20.04` image and never got a runner, so no
    test has actually executed since mid 2025. Now runs on `ubuntu-24.04`
  - `Schedule.autofill_slots` test called the method without its `interest_type` argument
- Security: login, password reset and X-App tokens were signed with a secret in the
  repository instead of the one in the environment

### Removed
- `GET /test-pdf-print` and the unrouted krysseliste PDF view
- Dockerfiles, `run_server.sh`, `restart.sh` and `_build/`. Production runs uWSGI behind
  Apache

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
