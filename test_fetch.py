import sys
sys.stdout = open('out.txt', 'w')
sys.stderr = open('err.txt', 'w')
try:
    from Agent.fetchAgent import fetch_and_print_responses
    print("Import successful")
    res = fetch_and_print_responses('1bOdh_d-w4FC3YnC0Fz41ufi-HF1g_t7vtCLydP077lw')
    print("Result:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
