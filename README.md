# DocAI ESG Parser

This repository includes a parser that can convert unstructured PDF docs into structured ESG GHG emissions data. It reads PDFs using the Doc AI form processor and parses the detected tables using a custom parser.

The custom parser checks for a configurable list of keywords in the cell contents and logs the captured fields to standard output.

