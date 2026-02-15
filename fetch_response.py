import requests
resp = requests.post("http://localhost:7071/api/reasoning", json={"query":"Summarize sensitive data labels in Purview."})
with open("resp_bytes.bin", "wb") as f:
    f.write(resp.content)
print("Wrote", len(resp.content), "bytes to resp_bytes.bin")