from docx import Document
from pathlib import Path
p=Path(r"C:\Users\anju2\Desktop\Advance_java_research\version-1.1aHome_Energy_Tracker-publication_updated.docx")
doc=Document(str(p))
for i, s in enumerate(doc.inline_shapes):
 print(i, s.width, s.height, round(s.width/914400,3), round(s.height/914400,3))
