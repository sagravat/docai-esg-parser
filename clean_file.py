import glob

# Using readlines()
file = open('table_data2.txt', 'r')
lines = file.readlines()
  
files = glob.glob(f'/Users/agravat/Work/octo/sector-data/need-review/**/*.pdf')
sectors = set()
for f in files:
    sector, filename = f.split("/")[-2:]
    sectors.add(sector)

# Strips the newline character
for line in lines:
    element = line.split("\t")[0]
    if not line.startswith("processing") and element in sectors and line.strip() != "":
        if len(line.split("\t")) == 5:
            fields = line.split("\t")
            try:
                scope_value = float(fields[-1].replace(",", "").replace(" ", "").replace("*", ""))
                print(f"{fields[0]}\t{fields[1]}\t{fields[2]}\t{fields[3]}\t{scope_value}")
            except Exception as e:
                # print(e)
                pass