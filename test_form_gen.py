from Agent.formAgent import process_rules_into_form
try:
    print(process_rules_into_form(["Must know Python", "Must be available immediately"]))
except Exception as e:
    import traceback
    traceback.print_exc()
