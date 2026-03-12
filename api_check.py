import json
import urllib.request
try:
    req = urllib.request.Request("http://127.0.0.1:5000/fetch-responses/1bOdh_d-w4FC3YnC0Fz41ufi-HF1g_t7vtCLydP077lw")
    with urllib.request.urlopen(req) as response:
        data = response.read()
        print("Success:", data)
except urllib.error.HTTPError as e:
    data = e.read()
    with open('error_output.txt', 'wb') as f:
        f.write(data)
    print("Saved error to error_output.txt")
