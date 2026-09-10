import asyncio
import httpx

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000/api/v1") as client:
        # Check health
        res = await client.get("/health/liveness")
        print("Liveness:", res.status_code, res.json())

if __name__ == "__main__":
    asyncio.run(main())
