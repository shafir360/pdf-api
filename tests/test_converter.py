import pathlib
from app.core.converter import pdf_bytes_to_dict

def test_dummy_pdf():
    pdf_path = pathlib.Path("dummy_data/948900-01_Application_Details.pdf")
    data = pdf_bytes_to_dict(pdf_path.read_bytes())
    assert data["first_name"]  # make sure something was extracted
    print(data)

