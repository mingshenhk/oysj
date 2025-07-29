input_file = "wiki.txt"
output_file = "target.txt"
max_lines = 2000

with open(input_file, "r", encoding="utf-8") as fin, \
     open(output_file, "w", encoding="utf-8") as fout:
    
    for i, line in enumerate(fin):
        if i >= max_lines:
            break
        fout.write(line)
