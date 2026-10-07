---
description: Git hygiene reminders for this paper project
---

## During work sessions

After completing any of these, prompt the user to commit:
- Finishing a section or subsection revision
- Adding or modifying figures
- Adding bibliography entries
- Any change that took more than 10 minutes of back-and-forth

Suggested prompt: "That's a good stopping point — want to commit?"

## Commit message format

```
<short summary line>

- Bullet points for specific changes
- Reference figures, citations, sections by name
```

## End of session

Before ending a session, check:
1. `git status` — anything uncommitted?
2. `git push` — anything unpushed?

If yes to either, prompt: "You have uncommitted/unpushed changes. Want to save your work?"

## Frequency target

Aim for commits every 15-30 minutes of active editing, or after each logical unit of work.
