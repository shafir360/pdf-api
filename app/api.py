"""All HTTP routes for the service."""
import os

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.converter import pdf_bytes_to_dict


from fastapi.responses import FileResponse

import io
from app.core.cv import cv_json_to_docx


from fastapi.responses import StreamingResponse

from app.core.cv_maker import cv_json_to_docx


import io
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict                
                






router = APIRouter()
MAX_SIZE_MB = int(os.getenv("MAX_SIZE_MB", "10"))  # configurable guard-rail


@router.post("/convert", response_class=JSONResponse, summary="Convert PDF to JSON")
async def convert_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Only PDF uploads are supported.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"PDF larger than allowed limit of {MAX_SIZE_MB} MB."
        )

    data = pdf_bytes_to_dict(pdf_bytes)
    return data


@router.post(
    "/health-check",
    status_code=status.HTTP_200_OK,
    summary="Simple empty-body health check",
    description="Responds 200 + {'status':'ok'} to any POST (body ignored)."
)
async def health_check():
    """
    Simple empty-body health check.
    """
    return {"status": "ok"}




# ──────────────────── 1. Pydantic model with aliases ──────────────────────────
class CVPayload(BaseModel):
    personal:       dict = Field(default_factory=dict,  alias="personal_details")
    contact:        dict = Field(default_factory=dict)
    education:      list = Field(default_factory=list, alias="education_history")
    experience:     list = Field(default_factory=list, alias="employment_history")
    skills:         list = Field(default_factory=list)
    projects:       list = Field(default_factory=list)
    certifications: list = Field(default_factory=list)
    languages:      list = Field(default_factory=list, alias="language_qualifications")
    interests:      list = Field(default_factory=list)

    # ---------------- Pydantic v2 ----------------
    model_config = ConfigDict(
        populate_by_name=True,   # accept either alias or field name
        extra="forbid"           # raise 422 on unknown keys (safer)
    )

    # -------- Uncomment this block instead for Pydantic v1 --------
    # class Config:
    #     allow_population_by_field_name = True
    #     extra = "forbid"


# ──────────────────── 2. Endpoint definition ──────────────────────────────────
@router.post(
    "/generate-cv",
    summary="Generate a Word CV from JSON",
    response_description="Streams back a .docx file",
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}
            }
        }
    }
)

async def generate_cv(payload: CVPayload = Body(...)):
    """
    Turn the structured CV payload into a Word document.
    Accepts both the new and legacy field names thanks to aliases.
    """
    try:
        # v2 → .model_dump(); for v1 use .dict()
        cv_dict = payload.model_dump()           # canonical keys only
        docx_bytes: bytes = cv_json_to_docx(cv_dict)
    except Exception as exc:                     # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"CV generation failed: {exc}"
        ) from exc

    # ── prepare streaming response ────────────────────────────────────────────
    file_obj = io.BytesIO(docx_bytes)
    file_obj.seek(0)

    # Nice-looking filename, falls back to just “cv.docx”
    first = payload.personal.get("first_name", "").strip()
    last  = payload.personal.get("last_name", "").strip()
    filename = (f"{first}-{last}" if first or last else "cv") + ".docx"

    return StreamingResponse(
        file_obj,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'}
    )