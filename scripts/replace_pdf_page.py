#!/usr/bin/env python3
# Usage: python replace_page.py <source.pdf> <source_page> <target.pdf> <target_page>

import sys
import tempfile
import os
from pypdf import PdfReader, PdfWriter

source_path, source_page, target_path, target_page = sys.argv[1:]
source_page, target_page = int(source_page) - 1, int(target_page) - 1

source = PdfReader(source_path)
target = PdfReader(target_path)
writer = PdfWriter()

for i, page in enumerate(target.pages):
    writer.add_page(source.pages[source_page] if i == target_page else page)

# Write to temp file first, then replace (safe in-place)
tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
writer.write(tmp)
tmp.close()
os.replace(tmp.name, target_path)

print(
    f"Done: page {source_page+1} of {source_path} → page {target_page+1} of {target_path}"
)
