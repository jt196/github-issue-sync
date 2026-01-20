# Plan Template

Copy this file to `plan-template.md` and customize for your project.
The `plan-template.md` file is gitignored, so your customizations stay local.

---

## Recommended Plan Format

```markdown
# Plan: Issue #XX - [Title]

**Problem:**
[What's broken - 1 sentence]

**Root Cause:**
[Why it's happening - 1 sentence]

**Files to Change:**
- `path/to/file.py` - [what to change]
- `path/to/other.js` - [what to change]

**Implementation Steps:**
1. [First change]
2. [Second change]
3. [Third change]

**Test:**
[How to verify the fix works]
```

---

## Example Plan

```markdown
# Plan: Issue #42 - Login fails on mobile

**Problem:**
Users can't log in on mobile Safari - form submits but nothing happens.

**Root Cause:**
Touch event not triggering form submit handler due to passive listener.

**Files to Change:**
- `src/components/LoginForm.tsx` - Add { passive: false } to touch handler
- `src/styles/login.css` - Fix button tap highlight

**Implementation Steps:**
1. In LoginForm.tsx line 45, change addEventListener options
2. Add -webkit-tap-highlight-color to button styles
3. Test on iOS Safari simulator

**Test:**
Open /login on mobile Safari, submit form, verify redirect to dashboard.
```

---

## Tips

### Keep It Short
- 1 sentence for problem/root cause
- Bullet points for files
- Numbered steps for implementation

### Be Specific
- Include file paths and line numbers when known
- Name functions/components to modify
- Specify exact test steps

### Skip the Plan If
- It's a typo fix
- The issue already has step-by-step instructions
- It's a single config change
