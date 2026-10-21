# User guide

## Student

Create an account with your own demo email/password. This project does not use UTA single sign-on. Never reuse your university password. After signing in:

1. **Explore resources:** search names, descriptions and tags. Select multiple category buttons to include any of those categories. Clear filters resets query and categories.
2. **View resource:** open a service for location, hours, contact, current notices, last-updated date, source and next steps. A green note shows the date the details were checked against the official page; an amber note means an administrator has not verified them yet.
3. **Saved resources:** bookmark a card or detail page. Remove the bookmark using the same button. Saved items are private to your account.
4. **Recently viewed:** opening a detail page updates your history. It keeps ten distinct services, newest first. Archived resources are hidden.
5. **Ask MavAssist:** use a question such as “I need help with tuition payment.” Do not enter personal/sensitive information. Each answer starts with a **Go to** slip naming the recommended office, why it fits, where it is, when it is open, how to contact it and when the details were last checked. Below it are the explanation with numbered sources, the steps to take and up to two other offices worth a look. If the question is unclear or outside campus services, MavAssist asks for a detail and suggests likely offices instead of guessing. Follow-up questions can use the previous topic. Verify the official resource before acting.
6. **Rate an answer:** choose Helpful or Not helpful once. Ratings feed anonymous aggregate analytics.
7. **Sign out:** ends your browser session. Tokens also expire after 60 minutes; sign in again when prompted.

## Administrator

An operator creates administrators using `python -m app.manage create-admin`; the public form creates only student accounts.

* **Manage resources / Services:** add/edit all displayed facts, source URL, tags and 2–3 next steps. Select a category. Tick “I checked these details against the official source” only after reviewing the current official page. Use the summary tiles, search, category filter and sort to find records; “Need source review” lists unverified ones. Saving in RAG mode rebuilds the embedding. Archive hides the service from student lists/search/chat; restore reverses this.
* **Categories:** add/rename categories. Delete only unused categories; retained analytics references also block deletion to preserve history.
* **Notices:** choose an active service, enter title/text, and local start/end times. Times are sent with timezone offsets. Only notices whose dates cover the current time appear to students. Edit or remove notices as needed.
* **Usage insights:** apply a date range to see totals, a daily activity chart (with a table view), common search terms, viewed offices, assistant topics and helpfulness. Empty ranges show no activity, not fabricated metrics.

## Accessibility

Keyboard navigation, visible focus, native labels, a skip-to-content link, native modal focus handling, reduced-motion support and responsive layouts are included. Screen readers receive loading/status/error feedback. Use browser zoom as needed. Automated checks cover the tested views; human keyboard/screen-reader and usability review remains necessary.
