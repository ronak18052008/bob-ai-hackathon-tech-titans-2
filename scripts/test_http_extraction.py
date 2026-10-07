import requests

login_res = requests.post(
    'http://127.0.0.1:8000/api/v1/auth/login',
    json={'email': 'dr.sarah.chen@demo-clinic.test', 'password': 'MedBrief2026!'}
)
if login_res.status_code != 200:
    print(f"Login failed: {login_res.status_code} {login_res.text}")
    exit(1)

token = login_res.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# List patients
patients = requests.get('http://127.0.0.1:8000/api/v1/patients', headers=headers).json().get('items', [])
print(f"Total patients: {len(patients)}")

target = next((p for p in patients if p['mrn'] == 'MRN-2026-9812'), None)
if not target:
    print("Test patient not found in list, listing all MRNs:")
    for p in patients:
        print(f"  {p['first_name']} {p['last_name']} - MRN: {p['mrn']} (ID: {p['id']})")
    # Use first patient
    target = patients[0]

p_id = target['id']
print(f"Selected patient: {target['first_name']} {target['last_name']} ({p_id})")

docs = requests.get(f'http://127.0.0.1:8000/api/v1/patients/{p_id}/documents', headers=headers).json()
print(f"Found {len(docs)} documents:")
for d in docs:
    print(f"\nDocument: {d['file_name']} (ID: {d['id']})")
    print(f"  Status: {d['status']}, Job Status: {d.get('job_status')}")
    
    # Trigger extraction
    ext_res = requests.post(f"http://127.0.0.1:8000/api/v1/documents/{d['id']}/extract", headers=headers)
    print(f"  Extraction HTTP code: {ext_res.status_code}")
    print(f"  Response: {ext_res.json()}")
