import asyncio
from httpx import AsyncClient, ASGITransport
from backend.app.main import app

async def run_checks():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r1 = await ac.get("/health")
        print("GET /health ->", r1.status_code, r1.json())

        r2 = await ac.get("/api/v1/farms")
        print("GET /api/v1/farms ->", r2.status_code, len(r2.json()))

        farm_payload = {
            "farm_id": "farm-peshawar-verify-01",
            "name": "Peshawar Verification Farm",
            "owner_name": "Tariq Khan",
            "contact_phone": "+92 300 1234567",
            "preferred_language": "ps",
            "location": {
                "latitude": 34.0151,
                "longitude": 71.5249,
                "district": "Peshawar",
                "province_or_region": "Khyber Pakhtunkhwa",
                "country": "Pakistan"
            },
            "boundary": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [71.522, 34.013],
                        [71.528, 34.013],
                        [71.528, 34.017],
                        [71.522, 34.017],
                        [71.522, 34.013]
                    ]
                ]
            },
            "total_area_hectares": 12.5,
            "soil_type": "alluvial_clay",
            "irrigation_source": "canal",
            "current_crops": ["Wheat"]
        }
        r3 = await ac.post("/api/v1/farms", json=farm_payload)
        print("POST /api/v1/farms ->", r3.status_code)

        r4 = await ac.get("/api/v1/farms/farm-peshawar-verify-01")
        print("GET /api/v1/farms/farm-peshawar-verify-01 ->", r4.status_code, r4.json().get("name"))

        # Crop History
        crop_payload = {
            "crop_name": "Wheat",
            "variety": "Fakhr-e-Sarhad",
            "season": "Rabi",
            "year": 2024,
            "area_planted_hectares": 10.0,
            "status": "growing"
        }
        r5 = await ac.post("/api/v1/farms/farm-peshawar-verify-01/crops", json=crop_payload)
        print("POST /api/v1/farms/{id}/crops ->", r5.status_code, r5.json().get("record_id"))

        # Assistant Chat
        chat_payload = {
            "session_id": "session-101",
            "message": "My farm has 12 hectares with canal water in Peshawar",
            "language": "en"
        }
        r6 = await ac.post("/api/v1/assistant/chat", json=chat_payload)
        print("POST /api/v1/assistant/chat ->", r6.status_code, r6.json().get("reply_message"))

if __name__ == "__main__":
    asyncio.run(run_checks())
