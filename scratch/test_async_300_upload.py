import asyncio
import httpx
import time

BASE_URL = "http://localhost:8000"

async def test_300_upload_flow():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Login user
        login_res = await client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": "proc_user_a@example.com",
            "password": "Password123!"
        })
        if login_res.status_code != 200:
            signup_res = await client.post(f"{BASE_URL}/api/v1/auth/signup", json={
                "email": "proc_user_a@example.com",
                "password": "Password123!",
                "full_name": "Proc User A"
            })
            token = signup_res.json()["access_token"]
        else:
            token = login_res.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # 2. Upload 300-page PDF
        print("Uploading test_300_pages.pdf...")
        t0 = time.time()
        with open("test_300_pages.pdf", "rb") as f:
            upload_res = await client.post(
                f"{BASE_URL}/api/v1/documents/upload",
                headers=headers,
                files={"file": ("test_300_pages.pdf", f, "application/pdf")}
            )
        elapsed = time.time() - t0
        print(f"Upload response received in {elapsed:.3f}s with status {upload_res.status_code}")
        assert upload_res.status_code == 201
        doc_data = upload_res.json()
        print(f"Doc ID: {doc_data['id']}, processing_status: {doc_data['processing_status']}, page_count: {doc_data['page_count']}")
        assert doc_data['processing_status'] in ['PENDING', 'PROCESSING']

        # 3. Test listing documents non-blocking
        t1 = time.time()
        list_res = await client.get(f"{BASE_URL}/api/v1/documents", headers=headers)
        list_elapsed = time.time() - t1
        print(f"List documents returned in {list_elapsed:.3f}s with status {list_res.status_code}")
        assert list_res.status_code == 200

if __name__ == "__main__":
    asyncio.run(test_300_upload_flow())
