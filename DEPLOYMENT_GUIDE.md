# Backend Deployment Guide (Roman English)

## A. Backend ko Railway aur Vercel par Deploy Karne Ka Tarika

### 1. Railway par Deploy Karna
- Railway par account banao (https://railway.app)
- New project create karo aur apna GitHub repo connect karo
- Project settings main jao aur Environment Variables section main jao
- Wahan par apni required environment variables add karo (neeche details hain)
- Deploy button par click karo

### 2. Vercel par Deploy Karna
- Vercel par account banao (https://vercel.com)
- New project create karo aur apna GitHub repo import karo
- Project settings main Environment Variables section main jao
- Wahan par apni required environment variables add karo
- Deploy button par click karo

## B. Environment Variables Main Kya Dalna Hai
- Agar aapka backend Firebase use karta hai aur `credentials/firebase-service-account.json` file hai, toh is file ka pura content aik environment variable main dalna hoga.
- Example:
  - Key: `FIREBASE_SERVICE_ACCOUNT`
  - Value: (poori json file ka content, bina line break ke ya base64 encode karke)

## C. GitHub Par Konsi Files Push Karni Hain
- Apna backend ka sara code push karo
- Lekin `credentials/firebase-service-account.json` ya koi bhi sensitive file push na karo
- `.gitignore` file main `credentials/` ya json file ka path add karo

## D. Code Main (main.py) Kya Changes Karni Hongi
- Firebase credentials ko file se load karne ke bajaye environment variable se load karo
- Example code:

```python
import os
import json

firebase_creds = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
if firebase_creds:
    creds_dict = json.loads(firebase_creds)
    # ab is dict ko firebase initialize main use karo
else:
    raise Exception('FIREBASE_SERVICE_ACCOUNT env variable not set')
```

- Agar aapko base64 encoding use karni ho toh:
```python
import os
import json
import base64

firebase_creds_b64 = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
if firebase_creds_b64:
    creds_json = base64.b64decode(firebase_creds_b64).decode('utf-8')
    creds_dict = json.loads(creds_json)
    # ab is dict ko firebase initialize main use karo
else:
    raise Exception('FIREBASE_SERVICE_ACCOUNT env variable not set')
```

## E. Summary
- Sensitive files kabhi bhi GitHub par push na karo
- Deployment platform par environment variables set karo
- Code main file ki bajaye env variable se credentials load karo
- .gitignore file update karo

---

Agar koi aur sawal ho toh pooch sakte hain!
