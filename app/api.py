"""All HTTP routes for the service."""
import os

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.converter import pdf_bytes_to_dict

from fastapi import Body
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import io
from app.core.cv import cv_json_to_docx


from fastapi.responses import StreamingResponse
import io
from app.core.cv_maker import cv_json_to_docx



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




class CVPayload(BaseModel):
    """Pydantic model mirroring the JSON contract above."""
    personal:       dict = Field(default_factory=dict)
    contact:        dict = Field(default_factory=dict)
    education:      list = Field(default_factory=list)
    experience:     list = Field(default_factory=list)
    skills:         list = Field(default_factory=list)
    projects:       list = Field(default_factory=list)
    certifications: list = Field(default_factory=list)
    languages:      list = Field(default_factory=list)
    interests:      list = Field(default_factory=list)


@router.post(
    "/generate-cv",
    summary="Generate a Word CV from JSON",
    response_description="Returns a .docx file"
)
async def generate_cv(payload: CVPayload = Body(...)):
    docx_bytes = cv_json_to_docx(payload.model_dump())

    buffer = io.BytesIO(docx_bytes)
    buffer.seek(0)                               # rewind before streaming

    filename = f"{payload.personal.get('first_name','cv')}-{payload.personal.get('last_name','')}.docx"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )