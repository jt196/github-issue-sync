# Plans Format Guide for Bubble.io Issues

## Keep It Short & Actionable

Plans are for **fixing Bubble workflows**, not writing essays. Focus on what to click in the Bubble editor.

## Good Plan Template

```markdown
# Plan: Issue #XX - [Title]

**Problem:**
[What's broken - 1 sentence]

**Root Cause:**
[Why - 1 sentence]

**Fix in Bubble Editor:**

**Workflow:** [workflow_id or name]
**Location:** Page/Element or Backend Workflows

**Steps:**
1. Open workflow [name/ID]
2. After Step X, add [Action Type] (e.g., "Schedule API Event on List")
3. Configure: [key settings to change]
4. Test: [how to verify]

**Current Flow:**
Step 1 → Step 2 → Step 3 (broken)

**New Flow:**
Step 1 → Step 2 → **NEW STEP** → Step 3 (fixed)
```

## Example: Issue #43

```markdown
# Plan: Issue #43 - Save Multiple Keywords

**Problem:**
Only saves 1 keyword when API returns a list.

**Root Cause:**
No loop after API call - single "Create Thing" instead of iterating results.

**Fix in Bubble Editor:**

**Workflow:** `bTJGp` (ButtonClicked on G:add_keyword_top)
**Location:** Dashboard page → G:add_keyword_top element

**Current Steps:**
1. API call → returns list of keywords
2. Create Thing → saves ONLY first result ❌

**What to Change:**
1. Click into Step 2 (Create Thing)
2. Check if "Result of Step 1" shows as a list or single item
3. If single item: API response may need `:items` accessor
4. If list already: Replace "Create Thing" with "Schedule API Event on List"
5. Point to new backend workflow that accepts single keyword parameter
6. That backend workflow does the "Create Thing"

**Or Simpler:**
If Bubble allows, change Step 2 to "Create a list of things" and iterate inline.

**Test:**
API returns 5 keywords → check Keywords table has 5 new records.
```

## What NOT to Include

- ❌ Long code examples (this is Bubble, not code)
- ❌ Migration notes for SvelteKit
- ❌ Exhaustive test case tables
- ❌ Multiple "phases" with subsections
- ❌ Explanations of what APIs do (we already know)

## What TO Include

- ✅ Specific workflow ID/name
- ✅ Which step number to change
- ✅ What action type to add/change
- ✅ Simple before/after flow diagram
- ✅ One-line test verification

## When to Skip a Plan

- Typo fixes
- Issues with clear repro steps already
- Simple "change this setting" fixes

## When to Write a Plan

- Multi-step workflow changes
- Unclear why something's broken
- Need to add new backend workflows
- Complex API → Database logic
