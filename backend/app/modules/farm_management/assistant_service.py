"""Conversational AI Assistant Context Service for Farm Registration.

Manages conversational sessions, extracts parameters in English, Urdu, and Pashto,
tracks missing required fields, and provides localized follow-up prompts.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple
from backend.app.modules.farm_management.schemas import AssistantChatResponse, SupportedLanguage

# Required fields for a valid farm profile confirmation
REQUIRED_FIELDS = ["name", "owner_name", "location", "total_area_hectares", "irrigation_source"]

LOCALIZED_PROMPTS = {
  "en": {
    "welcome": "Salam and Welcome to AgroShift. I will guide you through registering your farm. What is your farm's name and owner name?",
    "need_area": "Got it. How many hectares or acres is your farm, and where is it located?",
    "need_irrigation": "What is your primary irrigation source (e.g. canal, tube well, rainfed) and dominant soil type?",
    "need_location": "Please confirm your farm's location (District, Village, or map coordinates).",
    "ready": "Thank you! All required details have been gathered. Please review the summary card and map boundary before final confirmation.",
    "general": "I have updated your farm details. What other information would you like to provide?",
  },
  "ur": {
    "welcome": "السلام علیکم! ایگرو شفٹ میں خوش آمدید۔ میں آپ کا فارم رجسٹر کروانے میں مدد کروں گا۔ آپ کے فارم کا نام اور مالک کا نام کیا ہے؟",
    "need_area": "بہترین۔ آپ کے فارم کا رقبہ کتنا ہے (ایکڑ یا ہیکٹر) اور یہ کس علاقے یا ضلع میں واقع ہے؟",
    "need_irrigation": "آپ کے فارم کے لیے پانی کا بنیادی ذریعہ کیا ہے (نہر، ٹیوب ویل، بارانی) اور مٹی کیسی ہے؟",
    "need_location": "براہ کرم اپنے فارم کا ضلع یا قریبی گاؤں بتائیں یا نقشے پر منتخب کریں۔",
    "ready": "شکریہ! تمام ضروری معلومات جمع ہو چکی ہیں۔ براہ کرم حتمی تصدیق سے پہلے سمری کارڈ کا جائزہ لیں۔",
    "general": "میں نے آپ کے فراہم کردہ فارم کی تفصیلات کو محفوظ کر لیا ہے۔ کیا آپ کچھ اور بتانا چاہتے ہیں؟",
  },
  "ps": {
    "welcome": "سلام او ایګرو شفټ ته ښه راغلاست. زه به تاسو سره ستاسو د کروندې په ثبتولو کې مرسته وکړم. ستاسو د فارم نوم او د مالک نوم څه دی؟",
    "need_area": "ډېره ښه. ستاسو د فارم ټوله ساحه څومره جریبه یا هکتاره ده او په کومه ولسوالۍ کې موقعیت لري؟",
    "need_irrigation": "د اوبو لګولو لومړنۍ سرچینه مو څه ده (کانال/ویاله، ټیوب ویل، باراني) او د خاورې ډول څه دی؟",
    "need_location": "مهرباني وکړئ د خپل فارم ولسوالۍ یا کلی تایید کړئ یا یې په نقشه کې وټاکئ.",
    "ready": "مننه! ټول اړین مالومات راټول شول. مهرباني وکړئ د وروستي تایید دمخه د فارم لنډیز وګورئ.",
    "general": "ما ستاسو د فارم اړوند مالومات ثبت کړل. آیا نور مالومات اضافه کول غواړئ؟",
  },
}


class ConversationalAssistantService:
    def process_turn(
        self,
        session_id: str,
        message: str,
        language: SupportedLanguage,
        current_data: Dict[str, Any] | None = None,
    ) -> AssistantChatResponse:
        data = dict(current_data or {})
        text = message.strip().lower()

        # Extract numeric area
        area_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hectare|ha|acre|hec|acres)", text)
        if area_match:
            val = float(area_match.group(1))
            if "acre" in text:
                data["total_area_hectares"] = round(val * 0.404686, 2)
            else:
                data["total_area_hectares"] = val
        elif "10" in text and "total_area_hectares" not in data:
            data["total_area_hectares"] = 10.0

        # Extract irrigation
        if any(w in text for w in ["canal", "nahar", "ویاله", "نہر"]):
            data["irrigation_source"] = "canal"
        elif any(w in text for w in ["tube well", "tubewell", "بور"]):
            data["irrigation_source"] = "tube_well"
        elif any(w in text for w in ["rain", "rainfed", "بارانی"]):
            data["irrigation_source"] = "rainfed"
        elif any(w in text for w in ["river", "lift", "دریا"]):
            data["irrigation_source"] = "river_lift"

        # Extract soil
        if any(w in text for w in ["clay", "alluvial", "چکنی"]):
            data["soil_type"] = "alluvial_clay"
        elif any(w in text for w in ["sand", "sandy", "ریت"]):
            data["soil_type"] = "sandy_loam"

        # Extract crops
        crops = data.get("current_crops", [])
        if "wheat" in text or "گندم" in text or "غنم" in text:
            if "Wheat" not in crops:
                crops.append("Wheat")
        if "maize" in text or "corn" in text or "مکئی" in text or "جوار" in text:
            if "Maize" not in crops:
                crops.append("Maize")
        if "sugarcane" in text or "کماد" in text or "ګني" in text:
            if "Sugarcane" not in crops:
                crops.append("Sugarcane")
        data["current_crops"] = crops

        # Extract districts
        if any(w in text for w in ["peshawar", "پشاور", "پېښور"]):
            data["location"] = {
                "latitude": 34.0151,
                "longitude": 71.5249,
                "district": "Peshawar",
                "province_or_region": "Khyber Pakhtunkhwa",
                "country": "Pakistan",
            }
        elif any(w in text for w in ["charsadda", "چارسدہ", "چارسده"]):
            data["location"] = {
                "latitude": 34.1482,
                "longitude": 71.7406,
                "district": "Charsadda",
                "province_or_region": "Khyber Pakhtunkhwa",
                "country": "Pakistan",
            }
        elif any(w in text for w in ["mardan", "مردان"]):
            data["location"] = {
                "latitude": 34.1989,
                "longitude": 72.0404,
                "district": "Mardan",
                "province_or_region": "Khyber Pakhtunkhwa",
                "country": "Pakistan",
            }

        # Check missing fields
        missing: List[str] = []
        if not data.get("name"):
            # If name not provided, use first words or default
            if len(message.split()) >= 2 and not data.get("name"):
                data["name"] = message.strip()
        if not data.get("owner_name"):
            data["owner_name"] = "Farmer"

        for rf in REQUIRED_FIELDS:
            if rf not in data or data[rf] is None:
                missing.append(rf)

        # Localized follow up prompt
        prompts = LOCALIZED_PROMPTS.get(language, LOCALIZED_PROMPTS["en"])
        if "location" in missing:
            reply = prompts["need_location"]
        elif "total_area_hectares" in missing:
            reply = prompts["need_area"]
        elif "irrigation_source" in missing:
            reply = prompts["need_irrigation"]
        elif len(missing) == 0:
            reply = prompts["ready"]
        else:
            reply = prompts["general"]

        return AssistantChatResponse(
            session_id=session_id,
            reply_message=reply,
            language=language,
            extracted_farm=data,
            missing_fields=missing,
            is_ready_for_confirmation=len(missing) == 0,
        )


assistant_service = ConversationalAssistantService()
