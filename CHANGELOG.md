# CHANGELOG

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
