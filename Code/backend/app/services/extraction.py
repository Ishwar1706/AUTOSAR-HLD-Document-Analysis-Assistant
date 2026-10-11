import io,re
import fitz,cv2,numpy as np,pytesseract
from PIL import Image
from backend.app.config import settings
def quality(t):return 0 if not t else round(sum(c.isprintable() for c in t)/len(t),3)
def extract_pdf(path):
 d=fitz.open(path);out=[]
 for i,p in enumerate(d):
  native=p.get_text().strip();method='native';conf=None;text=native
  if settings.enable_ocr and len(native)<settings.ocr_min_native_characters:
   pix=p.get_pixmap(matrix=fitz.Matrix(settings.ocr_dpi/72,settings.ocr_dpi/72),alpha=False);img=np.array(Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB'));g=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY);g=cv2.adaptiveThreshold(g,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,31,11);data=pytesseract.image_to_data(g,lang=settings.ocr_language,config='--oem 3 --psm 6',output_type=pytesseract.Output.DICT);v=[float(x) for x in data['conf'] if str(x)!='-1'];conf=round(sum(v)/len(v),2) if v else 0;text=pytesseract.image_to_string(g,lang=settings.ocr_language,config='--oem 3 --psm 6').strip();method='ocr'
  sec=next((x.strip() for x in text.splitlines() if re.match(r'^\d+(?:\.\d+)*\s+',x.strip())),'Unknown section');out.append({'page':i+1,'text':text,'method':method,'ocr_confidence':conf,'quality':quality(text),'section':sec,'warning':'Low OCR confidence' if conf is not None and conf<settings.ocr_min_confidence else None})
 return out
def chunks(pages,source):
 out=[]
 for p in pages:
  for n,start in enumerate(range(0,len(p['text']),settings.chunk_size-settings.chunk_overlap)):
   t=p['text'][start:start+settings.chunk_size]
   if t.strip():out.append({'id':f'{source}-{p["page"]}-{n}','text':t,'metadata':{'source':source,'page':p['page'],'section':p['section'],'extraction_method':p['method']}})
 return out
