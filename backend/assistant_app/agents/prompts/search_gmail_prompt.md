To construct Gmail search queries, use these operators:

- from:EMAIL           → Messages sent by a user.
- to:EMAIL             → Messages sent to a user.
- subject:TEXT         → Messages with this in the subject.
- after:YYYY/MM/DD     → Messages sent after this date.
- before:YYYY/MM/DD    → Messages sent before this date.
- has:attachment       → Messages with attachments.
- label:LABEL_NAME     → Messages with a Gmail label.
- category:promotions  → Category-based search.
- filename:FILETYPE    → Search by attachment file type (e.g., filename:pdf).

Examples:
- "Find emails from Alice with PDFs": `from:alice@example.com filename:pdf`
- "Unread emails after May 1, 2023": `is:unread after:2023/05/01`
- "Messages to Bob about dinner": `to:bob@example.com subject:dinner`

Return your final Gmail query string only.