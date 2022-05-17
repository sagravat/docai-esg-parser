"""Extracts a table from PDF."""

import glob
import json
import os
import locale
import pprint
from collections import OrderedDict
from unicodedata import category

from absl import app
from absl import flags
from collections import defaultdict

from google.cloud import documentai_v1 as documentai
from google.api_core import exceptions

FLAGS = flags.FLAGS

flags.DEFINE_string('filename_prefix', '', 'The filename prefix, e.g. IT_CHINA.')
flags.DEFINE_string('input_dir', None, 'Input directory of PDF files.')
flags.DEFINE_string('output_dir', None,
                    'Output directory for converted text files.')
flags.DEFINE_string('project_id', None, 'GCP Numeric Project ID')
flags.DEFINE_string('processor_id', None, 'Doc AI Processor ID')
flags.DEFINE_string('location', 'us', 'Doc AI Processor location.')

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
pp = pprint.PrettyPrinter(indent=4)

DOC_MAP = defaultdict(list)

class ProcessDocumentError(Exception):
  pass


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def is_year_key(key):
    years = [str(y) for y in list(range(2015,2022))]
    fyyears1 = [f"FY{y}" for y in list(range(2015,2022))]
    fyyears2 = [f"FY{y}" for y in list(range(15,22))]
    fyyears3 = [f"FY {y}" for y in list(range(2015,2022))]
    fyyears4 = [f"FY {y}" for y in list(range(15,22))]
    years.extend(fyyears1)
    years.extend(fyyears2)
    years.extend(fyyears3)
    years.extend(fyyears4)
    for year in years:
        if key.startswith(year):
            return True
    return False

def get_cell_text(cell, text):
  """Convert a cell's segment data to its text form.

  Args:
    cell: A TableCell object.
    text: The text string of the document the cell belongs to.

  Returns:
    A string.
  """
  parts = []

  for segment in cell.layout.text_anchor.text_segments:
    part = text[segment.start_index:segment.end_index]
    parts.append(part)

  return "".join(parts).strip()

def has_scope1(text: str) -> bool:
  return "scope 1" in text.lower()

def process_scope_1_data(
    project_id: str, location: str, processor_id: str, file_path: str, output_dir: str
):
    from google.cloud import documentai_v1beta3 as documentai

    # You must set the api_endpoint if you use a location other than 'us', e.g.:
    opts = {}
    if location == "eu":
        opts = {"api_endpoint": "eu-documentai.googleapis.com"}

    client = documentai.DocumentProcessorServiceClient(client_options=opts)

    # The full resource name of the processor, e.g.:
    # projects/project-id/locations/location/processor/processor-id
    # You must create new processors in the Cloud Console first
    name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"

    with open(file_path, "rb") as image:
        image_content = image.read()

    # Read the file into memory
    document = {"content": image_content, "mime_type": "application/pdf"}

    # Configure the process request
    request = {"name": name, "raw_document": document}

    # Recognizes text entities in the PDF document
    result = client.process_document(request=request)

    #print("Document processing complete.")

    # Read the table and form fields output from the processor
    # The form processor also contains OCR data. For more information
    # on how to parse OCR data please see the OCR sample.
    # For a full list of Document object attributes, please reference this page: https://googleapis.dev/python/documentai/latest/_modules/google/cloud/documentai_v1beta3/types/document.html#Document
    document = result.document
    text = document.text

    data = []
    for page in document.pages:
      has_any_scope_1 = False
      for table in page.tables:
        cols = []
        header = table.header_rows[0]
        for cell in header.cells:
          cols.append(get_cell_text(cell, text))

        for row in table.body_rows:
          obj = {}

          has_scope_1 = False
          table_data = []
          od = OrderedDict()
          grouping = {}
          category = "NO_CATEGORY"

          for i, cell in enumerate(row.cells):
            key = cols[i]
            cell_text = get_cell_text(row.cells[i], text)
            if "scope 1" in cell_text.lower() or "scope 1" in cell_text.lower():
              has_scope_1 = True
              has_any_scope_1 = True
            
            obj[key] = cell_text
            if cell_text != "":
              table_data.append({
                'fieldValue': cell_text,
                'fieldName': cols[i] if cols[i] != "" else "NO_COL_HEADER",
                #'bounding': formVertices,
                # 'confidence':cell.layout.confidence clear
              })

          if has_scope_1:
            has_numeric_value = False
            has_year_key = False
            for item in table_data:
                fieldValue = item['fieldValue'].replace(',', '')
                # print("item: ", item)
                if fieldValue.isdigit() or is_number(fieldValue):
                    has_numeric_value = True
                    # print("has_numeric_value: ", item)
                    if is_year_key(item['fieldName']):
                        has_year_key = True
                        # print(item['fieldName'], item['fieldValue'])
                        # print("has_year: ", item)
                        break
            # print("done with for")
            if has_numeric_value and has_year_key:
                for i, item in enumerate(table_data):
                    if is_year_key(item['fieldName']):
                        # print(item['fieldName'], item['fieldValue'])
                        od[item['fieldName']] = item['fieldValue']
                    elif item['fieldName'] == "NO_COL_HEADER" and i == 0:
                        category = item['fieldValue'].replace("\n", " ")
                        x = 1
                grouping[category] = od
                # pp.pprint(od)
                x = 1
            elif has_numeric_value and not has_year_key:
                print("has numeric value but no year: ")
                pp.pprint(table_data)
                x = 2
            sector, filename = file_path.split("/")[-2:]
            company = filename.split(".pdf")[0]
            # print(sector, company)
            for category in grouping.keys():
                temp_od = grouping[category]
                for year in temp_od.keys():
                    val = temp_od[year].replace("\n", " ")
                    print(f"{sector}\t{company}\t{category}\t{year}\t{val}")
            if not has_numeric_value:
                print("non numeric scope 1 value")

            #pp.pprint(grouping)
      if len(page.tables) <= 0:
          print("no tables")
      elif not has_any_scope_1:
        print("no scope 1 in table")


def process_document_form_sample(
    project_id: str, location: str, processor_id: str, file_path: str, output_dir: str
):
    from google.cloud import documentai_v1beta3 as documentai

    # You must set the api_endpoint if you use a location other than 'us', e.g.:
    opts = {}
    if location == "eu":
        opts = {"api_endpoint": "eu-documentai.googleapis.com"}

    client = documentai.DocumentProcessorServiceClient(client_options=opts)

    # The full resource name of the processor, e.g.:
    # projects/project-id/locations/location/processor/processor-id
    # You must create new processors in the Cloud Console first
    name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"

    with open(file_path, "rb") as image:
        image_content = image.read()

    # Read the file into memory
    document = {"content": image_content, "mime_type": "application/pdf"}

    # Configure the process request
    request = {"name": name, "raw_document": document}

    # Recognizes text entities in the PDF document
    result = client.process_document(request=request)

    #print("Document processing complete.")

    # Read the table and form fields output from the processor
    # The form processor also contains OCR data. For more information
    # on how to parse OCR data please see the OCR sample.
    # For a full list of Document object attributes, please reference this page: https://googleapis.dev/python/documentai/latest/_modules/google/cloud/documentai_v1beta3/types/document.html#Document
    document = result.document
    text = document.text
    #print(f"Full document text: {repr(text)}\n")
    #print(f"There are {len(document.pages)} page(s) in this document.")

    # Read the text recognition output from the processor
    scope_1_index = -1
    for page in document.pages:
        # print(f"**** Page {page.page_number} ****")

        # print(f"Found {len(page.tables)} table(s):")
        data = []
        for table in page.tables:
          table_data = []
          cols = []

          # Right now we only handle the first header.
          # I'm not even clear what it means to have multiple headers.
          header = table.header_rows[0]
          for cell in header.cells:
            cols.append(get_cell_text(cell, text))

          table_map = defaultdict(list)
          for row in table.body_rows:
            obj = {}

            for i, cell in enumerate(row.cells):
              key = cols[i]
              # seg = []
              # for vertex in cell.layout.bounding_poly.normalized_vertices:
              #   seg.append({'x': vertex.x, 'y': vertex.y})
              
              cell_text = get_cell_text(cell, text)
              obj[key] = cell_text
              # if "scope 1" in cell_text.lower():
              #   print("SEGMENT: ", seg)

            table_data.append(obj)
          data.append(table_data)
        
        
        for i, table in enumerate(page.tables):
            # print("Table: ", table)
            num_columns = len(table.header_rows[0].cells)
            num_rows = len(table.body_rows)
            # print(f"Table with {num_columns} columns and {num_rows} rows:")
            table_text = print_table_rows(table, text)
            # print(table_text)
            if "scope 1" in table_text.lower() or "scope1" in table_text.lower():
              scope_1_index = i
              
        # print(f"Found {len(page.form_fields)} form fields:")
        # for field in page.form_fields:
        #     name = layout_to_text(field.field_name, text)
        #     value = layout_to_text(field.field_value, text)
        #     print(f"    * {repr(name.strip())}: {repr(value.strip())}")
    scope_1_text = False
    scope_1_data = False
    if scope_1_index >= 0:
      filename = file_path.split("/")[-1]
      print("write to ", filename)
      table_map = defaultdict(list)
      with open(f"{output_dir}/{filename}.txt", 'w') as fw:
        for d in data[scope_1_index]:
          # print(d)
          for key in d.keys():
            if has_scope1(key) or has_scope1(d[key]):
              scope_1_text = True

            if key == '':
              table_map['EMPTY_STRING'].append(d[key])
            else:
              table_map[key].append(d[key])

            if scope_1_text:
              value = d[key].replace("\n", " ")
              data_str = value.replace(',', '')
              if data_str.isdigit():
                print("\t (YES)", key.replace("\n", " "), ",", value, data_str)
              else:
                print("\t (NOPE)", key.replace("\n", " "), ",", value)
          scope_1_text = False
          fw.write(json.dumps(d))
          fw.write("\n")
        DOC_MAP[filename].append(table_map)
    else:
      print("GHG emissions not found")
    
def print_table_info(table: dict, text: str) -> None:
    # Print header row
    header_row_text = ""
    for header_cell in table.header_rows[0].cells:
        header_cell_text = layout_to_text(header_cell.layout, text)
        header_row_text += f"{repr(header_cell_text.strip())} | "
    #print(f"Columns: {header_row_text[:-3]}")
    # Print first body row
    body_row_text = ""
    for body_cell in table.body_rows[0].cells:
        body_cell_text = layout_to_text(body_cell.layout, text)
        body_row_text += f"{repr(body_cell_text.strip())} | "
    #print(f"First row data: {body_row_text[:-3]}\n")
    print(f"First row data: {body_row_text}\n")

    
def print_table_rows(table: dict, text: str) -> None:
    # Print header row
    table_text = ""
    header_row_text = ""
    for header_cell in table.header_rows[0].cells:
        header_cell_text = layout_to_text(header_cell.layout, text)
        header_row_text += f"{repr(header_cell_text.strip())} | "
        table_text += header_row_text
    #print(f"{header_row_text}")
    # Print first body row
    for row in table.body_rows:    
        body_row_text = ""
        for body_cell in row.cells:
            body_cell_text = layout_to_text(body_cell.layout, text)
            body_row_text += f"{repr(body_cell_text.strip())} | "
        table_text += body_row_text
        # print(f"{body_row_text}")
    # print("\n")
    return table_text

    
def layout_to_text(layout: dict, text: str) -> str:
    """
    Document AI identifies form fields by their offsets in the entirity of the
    document's text. This function converts offsets to a string.
    """
    response = ""
    # If a text segment spans several lines, it will
    # be stored in different text segments.
    for segment in layout.text_anchor.text_segments:
        start_index = (
            int(segment.start_index)
            if segment in layout.text_anchor.text_segments
            else 0
        )
        end_index = int(segment.end_index)
        response += text[start_index:end_index]
    return response


def main(unused_argv) -> None:
  # files = glob.glob(f'{FLAGS.input_dir}/{FLAGS.filename_prefix}*.pdf')
#   files = glob.glob(f'{FLAGS.input_dir}/Hardware/*.pdf')
#   files = glob.glob(f'{FLAGS.input_dir}/Airlines/*.pdf')
#   files = glob.glob(f'{FLAGS.input_dir}/Chemicals/*.pdf')
  files = glob.glob(f'{FLAGS.input_dir}/**/*.pdf')
#   files = glob.glob(f'{FLAGS.input_dir}/Biotechnology & Pharmaceuticals/*.pdf')
  for f in files:
    print(f'\nprocessing: {f}')
    try:
      process_scope_1_data(FLAGS.project_id, FLAGS.location, FLAGS.processor_id, f, FLAGS.output_dir)
      #process_document_form_sample(FLAGS.project_id, FLAGS.location, FLAGS.processor_id, f, FLAGS.output_dir)
    except ProcessDocumentError:
      pass
    except exceptions.InvalidArgument as e:
      print(e)
      pass
  # print(DOC_MAP)
  # with open("all_data.json", 'w') as fw:
  #   fw.write(json.dumps(DOC_MAP))


if __name__ == '__main__':
  app.run(main)
