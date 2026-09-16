import uno
from com.sun.star.beans import PropertyValue
from pathlib import Path
p=Path('/home/modou/dvwa-study/GROUPE-12/Rapport-DVWA.docx')
local=uno.getComponentContext()
resolver=local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver',local)
ctx=resolver.resolve('uno:socket,host=127.0.0.1,port=2012;urp;StarOffice.ComponentContext')
desktop=ctx.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop',ctx)
def prop(name,value):
 x=PropertyValue(); x.Name=name; x.Value=value; return x
doc=desktop.loadComponentFromURL(p.as_uri(),'_blank',0,(prop('Hidden',True),))
styles=doc.getStyleFamilies().getByName('ParagraphStyles')
for name in styles.getElementNames():
 if name.startswith('Contents'):
  style=styles.getByName(name)
  style.ParaTopMargin=0; style.ParaBottomMargin=50; style.CharHeight=10
 if name=='Code':
  styles.getByName(name).CharFontName='DejaVu Sans Mono'
indexes=doc.getDocumentIndexes()
for _ in range(2):
 for i in range(indexes.getCount()): indexes.getByIndex(i).update()
 doc.refresh()
doc.store()
doc.storeToURL(p.with_suffix('.pdf').as_uri(),(prop('FilterName','writer_pdf_Export'),prop('Overwrite',True)))
print('Index actualisés :',indexes.getCount())
doc.close(True)
desktop.terminate()
