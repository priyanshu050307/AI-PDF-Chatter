import io
import asyncio
import fitz
import sys
sys.path.insert(0, "backend")

from httpx import AsyncClient, ASGITransport
from app.main import app

async def reproduce():
    # Create sample PDF bytes
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((50, 50), "Digital Electronics by Anil K Maini\nSample Content for testing upload", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Signup/login test user
        signup_res = await client.post("/api/v1/auth/signup", json={
            "email": "test_upload_user@example.com",
            "password": "Password123!",
            "full_name": "Upload User"
        })
        if signup_res.status_code == 200:
            token = signup_res.json()["access_token"]
        else:
            login_res = await client.post("/api/v1/auth/login", json={
                "username": "test_upload_user@example.com",
                "password": "Password123!"
            })
            token = login_res.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # Upload file with spaces in name
        upload_res = await client.post(
            "/api/v1/documents/upload",
            headers=headers,
            files={"file": ("Digital electronics by Anil K Maini.pdf", pdf_bytes, "application/pdf")}
        )

        print(f"Upload Status: {upload_res.status_code}")
        print(f"Upload Response: {upload_res.json()}")

        if upload_res.status_code == 201:
            doc_id = upload_res.json()["id"]
            get_res = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
            print(f"Get Doc Status: {get_res.status_code}")
            print(f"Get Doc Response: {get_res.json()}")

if __name__ == "__main__":
    asyncio.run(reproduce())
