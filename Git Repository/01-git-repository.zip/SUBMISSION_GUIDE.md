# Project Deliverables upload mapping

Build the files using `python scripts/package_deliverables.py` from the repository
root. Upload each numbered file into the matching existing SkillWallet row:

| App deliverable | File in `submissions/` |
|---|---|
| 1. Git Repository | `01-git-repository.zip` |
| 2. Functional Web Application | `02-functional-web-application.zip` |
| 3. Database Schema & Data | `03-database-schema-and-data.sql` |
| 4. API Documentation | `04-api-documentation.md` |
| 5. Unit Tests | `05-unit-tests.zip` |

The application ZIP preserves the repository directory layout needed by the
database initializer and includes setup documentation. The unit-tests ZIP includes
the application and SQL dependencies so its tests can run after extraction.
The repository ZIP is the full source snapshot. ZIP packages exclude local secrets,
virtual environments, generated databases, caches, and the submissions directory.

For Git Repository, use the existing GitHub URL if the app offers a link field.
Otherwise upload its ZIP. If the app accepts only ZIP for documentation or SQL,
zip the respective single file without changing its contents.

GitHub Pages does not run this Python server. A public demo URL requires separate
Python hosting; local setup is documented and sufficient for running the submitted
application. Uploading files and pushing code are separate from clicking the app's
Submit for Evaluation control. Verify the five uploads before submitting.
