# New SWMS Generator

You are generating a FSC-compliant Safe Work Method Statement for an Australian construction project.

## Reference files
- Read docs/SWMS_GENERATOR_MASTER_v16_0.md for generation rules
- Read docs/SWMS_TASK_LIBRARY.md for task controls
- Use docs/SWMS_Template.docx as the output template
- Run src/swms_generator.py to produce the document

## Process
1. Ask the user for: PBCU, PC, site address, scope of works, tasks, plant/equipment, chemicals, emergency assembly point, emergency contact number
2. Confirm details back to user
3. Generate the SWMS using the master instructions
4. Output the completed .docx files
5. Run swms_bulletize.py on each output file to convert consolidated table to bullet format:
   ```
   PYTHONIOENCODING=utf-8 venv/Scripts/python.exe src/swms_bulletize.py output/<file>.docx output/<file>.docx
   ```

## Rules
- Always follow SWMS_GENERATOR_MASTER_v16_0.md
- FSC compliant language only
- Split tasks longer than 1800 characters
- Never skip the user input step
