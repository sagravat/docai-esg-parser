"""Procecesses a PDF file using a DocAI processor."""
from google.cloud import documentai_v1beta3 as documentai


def process_document(project_id: str, location: str, processor_id: str,
                     file_path: str) -> documentai.Document:
  """Process a document using a DocAI processor."""
  # You must set the api_endpoint if you use a location other than 'us', e.g.:
  opts = {}
  if location == 'eu':
    opts = {'api_endpoint': 'eu-documentai.googleapis.com'}

  client = documentai.DocumentProcessorServiceClient(client_options=opts)

  # The full resource name of the processor, e.g.:
  # projects/project-id/locations/location/processor/processor-id
  # You must create new processors in the Cloud Console first
  name = f'projects/{project_id}/locations/{location}/processors/{processor_id}'

  with open(file_path, 'rb') as image:
    image_content = image.read()

  # Read the file into memory
  document = {'content': image_content, 'mime_type': 'application/pdf'}

  # Configure the process request
  request = {'name': name, 'raw_document': document}

  # Recognizes text entities in the PDF document
  result = client.process_document(request=request)

  # Read the table and form fields output from the processor
  # The form processor also contains OCR data. For more information
  # on how to parse OCR data please see the OCR sample.
  # For a full list of Document object attributes, please reference this page:
  # https://googleapis.dev/python/documentai/latest/_modules/google/cloud/documentai_v1beta3/types/document.html#Document
  document = result.document

  return document
