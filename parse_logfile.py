"""Parses a log file and converts it into a tabular format."""

import glob
from absl import app
from absl import flags


FLAGS = flags.FLAGS

flags.DEFINE_string("logfile", None, "The full path to the log file.")
flags.DEFINE_string("input_dir", None, "Input directory of PDF files.")

flags.mark_flag_as_required('logfile')
flags.mark_flag_as_required('input_dir')


def main(unused_argv) -> None:
  file = open(FLAGS.logfile, "r")
  lines = file.readlines()

  files = glob.glob(f"{FLAGS.input_dir}/**/*.pdf")
  sectors = set()
  for f in files:
    sector, _ = f.split("/")[-2:]
    sectors.add(sector)

  # Strips the newline character
  for line in lines:
    element = line.split("\t")[0]
    if not line.startswith(
        "processing") and element in sectors and line.strip() != "":
      if len(line.split("\t")) == 5:
        fields = line.split("\t")
        try:
          scope_value_str = fields[-1].replace(",", "")
          scope_value_str = scope_value_str.replace(" ", "")
          scope_value_str = scope_value_str.replace("*", "")
          scope_value = float(scope_value_str)
          print(
              f"{fields[0]}\t{fields[1]}\t{fields[2]}\t{fields[3]}\t{scope_value}"
          )
        except Exception:
          # print(e)
          pass


if __name__ == "__main__":
  app.run(main)
