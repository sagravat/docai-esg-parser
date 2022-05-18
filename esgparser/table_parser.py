"""ESG Table Parser."""

import collections
import itertools
import pprint
from typing import Dict
from typing import List
from typing import Tuple

from google.cloud import documentai_v1beta3 as documentai

pp = pprint.PrettyPrinter(indent=4)


def _is_number(s):
  try:
    float(s)
    return True
  except ValueError:
    return False


def is_year_column(text: str) -> bool:
  """Check if the columnn header corresponds to the year."""
  years = [str(y) for y in list(range(2015, 2022))]
  fyyears1 = [f'FY{y}' for y in list(range(2015, 2022))]
  fyyears2 = [f'FY{y}' for y in list(range(15, 22))]
  fyyears3 = [f'FY {y}' for y in list(range(2015, 2022))]
  fyyears4 = [f'FY {y}' for y in list(range(15, 22))]
  years = list(itertools.chain(years, fyyears1, fyyears2, fyyears3, fyyears4))

  for year in years:
    if text.startswith(year):
      return True
  return False


def _has_keyword(text: str, keywords: List[str]) -> bool:
  """Check if the cell value contains any of the keywords."""
  return any(item in text.lower() for item in keywords)


def _get_cell_text(cell, text) -> str:
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

  return ''.join(parts).strip()


def _log_results(file_path: str, ghg_emissions_data: Dict[str, str]):
  """Output the fields in tab delimeted format."""
  sector, filename = file_path.split('/')[-2:]
  company = filename.split('.pdf')[0]
  for category in ghg_emissions_data.keys():
    temp_od = ghg_emissions_data[category]
    for year in temp_od.keys():
      val = temp_od[year].replace('\n', ' ')
      print(f'{sector}\t{company}\t{category}\t{year}\t{val}')


def _parse_extracted_cols(
    cols: List[Dict[str, str]]) -> Tuple[bool, Dict[str, str]]:
  """Check if the cells contain the year and numerical GHG emissions data."""
  has_numeric_value = False
  has_year_key = False
  category = 'NO_CATEGORY'
  ordered_data = collections.OrderedDict()
  ghg_emissions_data = {}

  for item in cols:
    field_value = item['fieldValue'].replace(',', '')
    if field_value.isdigit() or _is_number(field_value):
      has_numeric_value = True
      if is_year_column(item['fieldName']):
        has_year_key = True
        break
  if has_numeric_value and has_year_key:
    for i, item in enumerate(cols):
      if is_year_column(item['fieldName']):
        ordered_data[item['fieldName']] = item['fieldValue']
      elif item['fieldName'] == 'NO_COL_HEADER' and i == 0:
        category = item['fieldValue'].replace('\n', ' ')
    ghg_emissions_data[category] = ordered_data
  elif has_numeric_value and not has_year_key:
    print('has numeric value but no year: ')
    pp.pprint(cols)

  return has_numeric_value, ghg_emissions_data


def process_tabular_data(document: documentai.Document, file_path: str,
                         keywords: List[str]):
  """Process tables and parse each row by a list of keywords."""
  text = document.text
  for page in document.pages:
    has_any_keyword = False
    for table in page.tables:
      cols = []
      header = table.header_rows[0]
      for cell in header.cells:
        cols.append(_get_cell_text(cell, text))

      for row in table.body_rows:
        extracted_cols = []
        for i, cell in enumerate(row.cells):
          cell_text = _get_cell_text(row.cells[i], text)
          if _has_keyword(cell_text.lower(), keywords):
            has_any_keyword = True

          if cell_text:
            extracted_cols.append({
                'fieldValue': cell_text,
                'fieldName': cols[i] if cols[i] else 'NO_COL_HEADER',
            })

        if has_any_keyword:
          has_numeric_value, ghg_emissions_data = _parse_extracted_cols(
              extracted_cols)
          _log_results(file_path, ghg_emissions_data)
          # The row had GHG emissions attributes (e.g Scope 1) but no numerical
          # value for the amount.
          if not has_numeric_value:
            print('non numeric value')

    if len(page.tables) <= 0:
      print('no tables')
    elif not has_any_keyword:
      print('no keywords in table')
