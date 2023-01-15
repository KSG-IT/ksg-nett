# CHANGELOG

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
