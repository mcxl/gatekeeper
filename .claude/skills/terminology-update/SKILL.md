# Terminology Update
1. User provides: OLD_TERM and NEW_TERM
2. Run: grep -r "OLD_TERM" --include="*.py" to find all affected files
3. Edit each file, replacing OLD_TERM with NEW_TERM
4. Rebuild affected documents with python <filename>.py
5. Note any files that fail (e.g., locked Word docs)
6. Git add and commit with message: "Standardize terminology: OLD_TERM → NEW_TERM"
