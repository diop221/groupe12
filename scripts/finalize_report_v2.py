from pathlib import Path
import subprocess,time,uno
from com.sun.star.beans import PropertyValue
root=Path(__file__).resolve().parents[1]
proc=subprocess.Popen(['libreoffice','-env:UserInstallation=file:///tmp/dvwa-v2-final','--headless','--accept=socket,host=127.0.0.1,port=2013;urp;StarOffice.ServiceManager','--norestore'])
local=uno.getComponentContext(); resolver=local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver',local)
for _ in range(40):
 try:
  ctx=resolver.resolve('uno:socket,host=127.0.0.1,port=2013;urp;StarOffice.ComponentContext'); break
 except Exception: time.sleep(.25)
else: raise RuntimeError('LibreOffice indisponible')
desktop=ctx.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop',ctx)
def prop(n,v):
 p=PropertyValue(); p.Name=n; p.Value=v; return p
path=root/'GROUPE-12/Rapport-DVWA-V2.docx'
doc=desktop.loadComponentFromURL(path.as_uri(),'_blank',0,(prop('Hidden',True),))
indexes=doc.getDocumentIndexes()
for _ in range(3):
 for i in range(indexes.getCount()): indexes.getByIndex(i).update()
 doc.refresh()
doc.store()
doc.storeToURL(path.with_suffix('.pdf').as_uri(),(prop('FilterName','writer_pdf_Export'),prop('Overwrite',True)))
print('Index actualisés :',indexes.getCount())
doc.close(True); desktop.terminate(); proc.wait(timeout=20)
