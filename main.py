r"""Extracts GHG Emissions tabular data from PDFs.

Example usage:
python main.py --input_dir /path/to/pdf/folders --project_id 123456789
--processor_id b123abc --keywords "scope 1, scope 2"

"""

import glob

from absl import app
from absl import flags
from docai import helper
from esgparser import table_parser
from google.api_core import exceptions

FLAGS = flags.FLAGS

flags.DEFINE_string('input_dir', None, 'Input directory of PDF files.')
flags.DEFINE_string('output_dir', None,
                    'Output directory for converted text files.')
flags.DEFINE_string('project_id', None, 'GCP Numeric Project ID')
flags.DEFINE_string('processor_id', None, 'Doc AI Processor ID')
flags.DEFINE_string('location', 'us', 'Doc AI Processor location.')
flags.DEFINE_list('keywords', ['scope 1', 'scope 2', 'scope 3'],
                  'List of lowercase keywords to detect in table.')

flags.mark_flag_as_required('input_dir')
flags.mark_flag_as_required('project_id')
flags.mark_flag_as_required('processor_id')


class ProcessDocumentError(Exception):
  pass


def main(unused_argv) -> None:
  files = glob.glob(f'{FLAGS.input_dir}/**/*.pdf')
  for file in files:
    print(f'\nprocessing: {file}')
    try:
      document = helper.process_document(FLAGS.project_id, FLAGS.location,
                                         FLAGS.processor_id, file)
      table_parser.process_tabular_data(document, file, FLAGS.keywords)
    except ProcessDocumentError:
      pass
    except exceptions.InvalidArgument as e:
      print(e)
      pass


if __name__ == '__main__':
  app.run(main)
